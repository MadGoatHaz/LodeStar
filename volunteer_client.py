import hashlib
import json
import time
import threading
import requests
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import os
import uuid
from typing import Dict, Any, Optional

class VolunteerClient:
    def __init__(self, api_url: str = "http://localhost:5000"):
        """Initialize volunteer client"""
        self.api_url = api_url
        self.anonymous_id = self._generate_anonymous_id()
        self.private_key = None
        self.public_key = None
        self.is_running = False
        self.collection_thread = None
        self.submission_queue = []
        self.last_submission = 0
        
        # Generate key pair for signing
        self._generate_key_pair()
        
    def _generate_anonymous_id(self) -> str:
        """Generate anonymous ID for volunteer"""
        # Use UUID4 for anonymous ID generation
        return str(uuid.uuid4())
        
    def _generate_key_pair(self):
        """Generate RSA key pair for signing submissions"""
        # Generate private key
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Get public key
        self.public_key = self.private_key.public_key()
        
    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')
        
    def sign_data(self, data: Dict[str, Any]) -> str:
        """Sign data with private key"""
        # Convert data to JSON string and encode
        data_json = json.dumps(data, sort_keys=True)
        data_bytes = data_json.encode('utf-8')
        
        # Sign the data
        signature = self.private_key.sign(
            data_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # Encode signature as base64 for transmission
        return base64.b64encode(signature).decode('utf-8')
        
    def start_collection(self):
        """Start background data collection"""
        if not self.is_running:
            self.is_running = True
            self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
            self.collection_thread.start()
            print(f"Volunteer client started with ID: {self.anonymous_id}")
            
    def stop_collection(self):
        """Stop background data collection"""
        self.is_running = False
        if self.collection_thread:
            self.collection_thread.join()
        print("Volunteer client stopped")
        
    def _collection_loop(self):
        """Main collection loop"""
        while self.is_running:
            try:
                # Collect data (in a real implementation, this would collect actual data)
                data = self._collect_sample_data()
                if data:
                    self._queue_submission(data)
                    
                # Wait before next collection
                time.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                print(f"Error in collection loop: {e}")
                time.sleep(5)  # Wait 5 seconds before retrying
                
    def _collect_sample_data(self) -> Optional[Dict[str, Any]]:
        """Collect sample data (in a real implementation, this would collect actual content)"""
        # This is a placeholder - in a real implementation, this would:
        # 1. Monitor browser content
        # 2. Extract relevant information
        # 3. Validate and format the data
        
        # For demonstration, we'll generate sample data
        sample_data = {
            "type": "statement",
            "content": "This is a sample statement for demonstration purposes",
            "source": "sample_source",
            "timestamp": time.time(),
            "context": "Sample context information"
        }
        
        return sample_data
        
    def _queue_submission(self, data: Dict[str, Any]):
        """Queue data for submission"""
        # Add to submission queue
        self.submission_queue.append(data)
        
        # Submit if queue has enough items or enough time has passed
        if len(self.submission_queue) >= 5 or (time.time() - self.last_submission) > 300:
            self._submit_batch()
            
    def _submit_batch(self):
        """Submit batch of collected data"""
        if not self.submission_queue:
            return
            
        try:
            # Prepare batch data
            batch_data = {
                "volunteer_id": self.anonymous_id,
                "submissions": [],
                "public_key": self.get_public_key_pem(),
                "timestamp": time.time()
            }
            
            # Process each item in queue
            for data in self.submission_queue:
                # Add hash for integrity verification
                data_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
                
                # Sign the data
                signature = self.sign_data(data)
                
                # Add to batch
                batch_data["submissions"].append({
                    "data": data,
                    "hash": data_hash,
                    "signature": signature
                })
                
            # Submit batch
            response = requests.post(
                f"{self.api_url}/api/volunteer/submit_batch",
                json=batch_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"Submitted batch of {len(batch_data['submissions'])} items")
                # Clear queue on successful submission
                self.submission_queue.clear()
                self.last_submission = time.time()
            else:
                print(f"Submission failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error submitting batch: {e}")
            
    def submit_single_item(self, data: Dict[str, Any]):
        """Submit a single item immediately"""
        try:
            # Add hash for integrity verification
            data_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            
            # Sign the data
            signature = self.sign_data(data)
            
            # Prepare submission
            submission = {
                "volunteer_id": self.anonymous_id,
                "data": data,
                "hash": data_hash,
                "signature": signature,
                "public_key": self.get_public_key_pem(),
                "timestamp": time.time()
            }
            
            # Submit
            response = requests.post(
                f"{self.api_url}/api/volunteer/submit",
                json=submission,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print("Item submitted successfully")
                return True
            else:
                print(f"Submission failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error submitting item: {e}")
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        return {
            "anonymous_id": self.anonymous_id,
            "is_running": self.is_running,
            "queue_size": len(self.submission_queue),
            "last_submission": self.last_submission,
            "public_key_hash": hashlib.sha256(self.get_public_key_pem().encode()).hexdigest()[:16]
        }
        
    def load_configuration(self, config_file: str = "volunteer_config.json"):
        """Load configuration from file"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # In a real implementation, we would load settings from config
                    print(f"Configuration loaded from {config_file}")
                    return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
        return {}
        
    def save_configuration(self, config: Dict[str, Any], config_file: str = "volunteer_config.json"):
        """Save configuration to file"""
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Configuration saved to {config_file}")
        except Exception as e:
            print(f"Error saving configuration: {e}")

# Browser-based JavaScript client (for reference)
BROWSER_CLIENT_JS = """
class BrowserVolunteerClient {
    constructor(apiUrl = 'http://localhost:5000') {
        this.apiUrl = apiUrl;
        this.anonymousId = this.generateAnonymousId();
        this.isRunning = false;
        this.submissionQueue = [];
        this.lastSubmission = 0;
        this.worker = null;
    }
    
    generateAnonymousId() {
        // Generate anonymous ID using crypto API
        if (window.crypto && window.crypto.getRandomValues) {
            const array = new Uint32Array(4);
            window.crypto.getRandomValues(array);
            return Array.from(array, dec => dec.toString(16)).join('');
        }
        // Fallback to Math.random (less secure)
        return 'anon_' + Math.random().toString(36).substr(2, 9);
    }
    
    async startCollection() {
        if (!this.isRunning) {
            this.isRunning = true;
            // Start background collection using Web Worker
            this.startWorker();
            console.log(`Browser volunteer client started with ID: ${this.anonymousId}`);
        }
    }
    
    stopCollection() {
        this.isRunning = false;
        if (this.worker) {
            this.worker.terminate();
            this.worker = null;
        }
        console.log("Browser volunteer client stopped");
    }
    
    startWorker() {
        // Create Web Worker for background collection
        const workerCode = `
            self.onmessage = function(e) {
                const { command, apiUrl, anonymousId } = e.data;
                
                if (command === 'collect') {
                    // Collect data from current page
                    const data = {
                        type: 'web_content',
                        content: document.body.innerText.substring(0, 1000),
                        url: window.location.href,
                        title: document.title,
                        timestamp: Date.now()
                    };
                    
                    // Send data back to main thread
                    self.postMessage({ type: 'data_collected', data: data });
                }
            };
        `;
        
        const blob = new Blob([workerCode], { type: 'application/javascript' });
        this.worker = new Worker(URL.createObjectURL(blob));
        
        // Handle messages from worker
        this.worker.onmessage = (e) => {
            if (e.data.type === 'data_collected') {
                this.queueSubmission(e.data.data);
            }
        };
        
        // Start collection loop
        this.collectionLoop();
    }
    
    collectionLoop() {
        if (this.isRunning) {
            // Send collection command to worker
            if (this.worker) {
                this.worker.postMessage({
                    command: 'collect',
                    apiUrl: this.apiUrl,
                    anonymousId: this.anonymousId
                });
            }
            
            // Schedule next collection
            setTimeout(() => this.collectionLoop(), 30000); // 30 seconds
        }
    }
    
    queueSubmission(data) {
        // Add to submission queue
        this.submissionQueue.push(data);
        
        // Submit if queue has enough items or enough time has passed
        if (this.submissionQueue.length >= 5 || (Date.now() - this.lastSubmission) > 300000) {
            this.submitBatch();
        }
    }
    
    async submitBatch() {
        if (this.submissionQueue.length === 0) return;
        
        try {
            const batchData = {
                volunteer_id: this.anonymousId,
                submissions: this.submissionQueue,
                timestamp: Date.now()
            };
            
            const response = await fetch(`${this.apiUrl}/api/volunteer/submit_batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(batchData)
            });
            
            if (response.ok) {
                console.log(`Submitted batch of ${this.submissionQueue.length} items`);
                // Clear queue on successful submission
                this.submissionQueue = [];
                this.lastSubmission = Date.now();
            } else {
                console.error(`Submission failed: ${response.status} - ${await response.text()}`);
            }
        } catch (error) {
            console.error('Error submitting batch:', error);
        }
    }
    
    getStatus() {
        return {
            anonymousId: this.anonymousId,
            isRunning: this.isRunning,
            queueSize: this.submissionQueue.length,
            lastSubmission: this.lastSubmission
        };
    }
}

// Auto-initialize browser client when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on the volunteer page
    if (window.location.pathname.includes('volunteer')) {
        window.volunteerClient = new BrowserVolunteerClient();
        window.volunteerClient.startCollection();
    }
});
"""

# Example usage
if __name__ == "__main__":
    # Initialize volunteer client
    client = VolunteerClient("http://localhost:5000")
    
    # Print client status
    print("Client Status:", client.get_status())
    
    # Start collection
    client.start_collection()
    
    # Let it run for a bit
    time.sleep(10)
    
    # Stop collection
    client.stop_collection()