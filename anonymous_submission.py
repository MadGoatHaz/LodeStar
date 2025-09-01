import hashlib
import json
import time
import threading
import base64
import random
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from typing import Dict, List, Any, Optional
import requests
import socks
import socket
from urllib.parse import urlparse

class OnionRouter:
    def __init__(self, api_url: str = "http://localhost:5000"):
        """Initialize onion router for anonymous submissions"""
        self.api_url = api_url
        self.onion_routers = self._get_onion_routers()
        self.session_keys = {}  # session_id -> list of encryption keys
        self.routing_stats = {
            'total_routed': 0,
            'successful_submissions': 0,
            'failed_submissions': 0
        }
        self.lock = threading.Lock()
        
    def _get_onion_routers(self) -> List[Dict[str, Any]]:
        """Get list of available onion routers"""
        # In a real implementation, this would fetch from a distributed directory
        # For now, we'll simulate with local routing
        return [
            {"id": "router_1", "address": "127.0.0.1:9050", "public_key": "key1"},
            {"id": "router_2", "address": "127.0.0.1:9051", "public_key": "key2"},
            {"id": "router_3", "address": "127.0.0.1:9052", "public_key": "key3"}
        ]
        
    def generate_session_id(self) -> str:
        """Generate anonymous session ID"""
        return hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        
    def create_onion_route(self, data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Create onion-routed submission"""
        # Select random path through onion routers
        path_length = random.randint(3, 5)  # 3-5 hops
        selected_routers = random.sample(self.onion_routers, min(path_length, len(self.onion_routers)))
        
        # Generate encryption keys for each hop
        encryption_keys = []
        for router in selected_routers:
            # In a real implementation, we would use the router's public key
            # For simulation, we'll generate symmetric keys
            key = hashlib.sha256(f"{session_id}_{router['id']}".encode()).digest()[:32]
            encryption_keys.append(key)
            
        # Store keys for this session
        self.session_keys[session_id] = encryption_keys
        
        # Encrypt data for each layer (onion encryption)
        encrypted_data = self._layered_encrypt(data, encryption_keys)
        
        # Create onion packet
        onion_packet = {
            "session_id": session_id,
            "path": [router['id'] for router in selected_routers],
            "encrypted_payload": base64.b64encode(encrypted_data).decode(),
            "timestamp": time.time()
        }
        
        return onion_packet
        
    def _layered_encrypt(self, data: Dict[str, Any], keys: List[bytes]) -> bytes:
        """Apply layered encryption (onion encryption)"""
        # Convert data to JSON
        data_json = json.dumps(data, sort_keys=True)
        data_bytes = data_json.encode()
        
        # Encrypt from innermost to outermost layer
        encrypted_data = data_bytes
        for key in reversed(keys):
            # In a real implementation, we would use proper encryption
            # For simulation, we'll use simple XOR with key
            encrypted_data = self._xor_encrypt(encrypted_data, key)
            
        return encrypted_data
        
    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR encryption for simulation"""
        key_len = len(key)
        return bytes([data[i] ^ key[i % key_len] for i in range(len(data))])
        
    def submit_anonymously(self, data: Dict[str, Any]) -> bool:
        """Submit data through onion routing"""
        session_id = self.generate_session_id()
        
        try:
            # Create onion route
            onion_packet = self.create_onion_route(data, session_id)
            
            # Submit through API
            response = requests.post(
                f"{self.api_url}/api/volunteer/anonymous_submit",
                json=onion_packet,
                headers={"Content-Type": "application/json"}
            )
            
            with self.lock:
                self.routing_stats['total_routed'] += 1
                if response.status_code == 200:
                    self.routing_stats['successful_submissions'] += 1
                    print(f"Anonymous submission successful for session {session_id}")
                    return True
                else:
                    self.routing_stats['failed_submissions'] += 1
                    print(f"Anonymous submission failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            with self.lock:
                self.routing_stats['total_routed'] += 1
                self.routing_stats['failed_submissions'] += 1
            print(f"Error in anonymous submission: {e}")
            return False
            
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get onion routing statistics"""
        with self.lock:
            total = self.routing_stats['total_routed']
            success_rate = (
                self.routing_stats['successful_submissions'] / total * 100
                if total > 0 else 0
            )
            
            return {
                **self.routing_stats,
                'success_rate': round(success_rate, 2)
            }
            
    def cleanup_session(self, session_id: str):
        """Clean up session keys"""
        with self.lock:
            if session_id in self.session_keys:
                del self.session_keys[session_id]

class BatchedSubmission:
    def __init__(self, api_url: str = "http://localhost:5000", batch_size: int = 10):
        """Initialize batched submission system"""
        self.api_url = api_url
        self.batch_size = batch_size
        self.submission_queue = []
        self.last_submission = 0
        self.batch_stats = {
            'batches_submitted': 0,
            'items_submitted': 0,
            'failed_batches': 0
        }
        self.lock = threading.Lock()
        self.onion_router = OnionRouter(api_url)
        
    def queue_submission(self, data: Dict[str, Any]):
        """Queue data for batched submission"""
        with self.lock:
            self.submission_queue.append(data)
            
            # Submit batch if queue is full or enough time has passed
            if (len(self.submission_queue) >= self.batch_size or 
                (time.time() - self.last_submission) > 300):  # 5 minutes
                self._submit_batch()
                
    def _submit_batch(self):
        """Submit batch of queued data"""
        if not self.submission_queue:
            return
            
        try:
            # Prepare batch
            batch_data = {
                "submissions": self.submission_queue.copy(),
                "batch_size": len(self.submission_queue),
                "timestamp": time.time()
            }
            
            # Submit through onion routing for anonymity
            success = self.onion_router.submit_anonymously(batch_data)
            
            with self.lock:
                if success:
                    self.batch_stats['batches_submitted'] += 1
                    self.batch_stats['items_submitted'] += len(self.submission_queue)
                    self.submission_queue.clear()
                    self.last_submission = time.time()
                else:
                    self.batch_stats['failed_batches'] += 1
                    
        except Exception as e:
            with self.lock:
                self.batch_stats['failed_batches'] += 1
            print(f"Error submitting batch: {e}")
            
    def get_batch_stats(self) -> Dict[str, Any]:
        """Get batch submission statistics"""
        with self.lock:
            total_batches = self.batch_stats['batches_submitted'] + self.batch_stats['failed_batches']
            success_rate = (
                self.batch_stats['batches_submitted'] / total_batches * 100
                if total_batches > 0 else 0
            )
            
            return {
                **self.batch_stats,
                'queue_size': len(self.submission_queue),
                'success_rate': round(success_rate, 2)
            }

class SecureTransmission:
    def __init__(self):
        """Initialize secure transmission system"""
        self.encryption_stats = {
            'data_encrypted': 0,
            'encryption_errors': 0
        }
        self.lock = threading.Lock()
        
    def encrypt_data(self, data: Dict[str, Any], public_key_pem: str) -> Dict[str, Any]:
        """Encrypt data with public key"""
        try:
            # Load public key
            from cryptography.hazmat.primitives import serialization
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )
            
            # Convert data to JSON
            data_json = json.dumps(data, sort_keys=True)
            data_bytes = data_json.encode()
            
            # Encrypt data
            encrypted_data = public_key.encrypt(
                data_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Encode as base64 for transmission
            encrypted_b64 = base64.b64encode(encrypted_data).decode()
            
            with self.lock:
                self.encryption_stats['data_encrypted'] += 1
                
            return {
                "encrypted_data": encrypted_b64,
                "encryption_method": "RSA-OAEP",
                "timestamp": time.time()
            }
            
        except Exception as e:
            with self.lock:
                self.encryption_stats['encryption_errors'] += 1
            print(f"Error encrypting data: {e}")
            raise
            
    def get_encryption_stats(self) -> Dict[str, Any]:
        """Get encryption statistics"""
        with self.lock:
            total = self.encryption_stats['data_encrypted'] + self.encryption_stats['encryption_errors']
            success_rate = (
                self.encryption_stats['data_encrypted'] / total * 100
                if total > 0 else 0
            )
            
            return {
                **self.encryption_stats,
                'success_rate': round(success_rate, 2)
            }

# Integration with volunteer client
class SecureVolunteerClient:
    def __init__(self, api_url: str = "http://localhost:5000"):
        """Initialize secure volunteer client"""
        self.api_url = api_url
        self.anonymous_id = self._generate_anonymous_id()
        self.batched_submission = BatchedSubmission(api_url)
        self.secure_transmission = SecureTransmission()
        self.is_running = False
        self.collection_thread = None
        
    def _generate_anonymous_id(self) -> str:
        """Generate anonymous ID"""
        return hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        
    def start_collection(self):
        """Start secure background collection"""
        if not self.is_running:
            self.is_running = True
            self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
            self.collection_thread.start()
            print(f"Secure volunteer client started with ID: {self.anonymous_id}")
            
    def stop_collection(self):
        """Stop background collection"""
        self.is_running = False
        if self.collection_thread:
            self.collection_thread.join()
        print("Secure volunteer client stopped")
        
    def _collection_loop(self):
        """Main collection loop with secure submission"""
        while self.is_running:
            try:
                # Collect data (in a real implementation, this would collect actual data)
                data = self._collect_sample_data()
                if data:
                    # Queue for secure batched submission
                    self.batched_submission.queue_submission(data)
                    
                # Wait before next collection
                time.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                print(f"Error in secure collection loop: {e}")
                time.sleep(5)  # Wait 5 seconds before retrying
                
    def _collect_sample_data(self) -> Optional[Dict[str, Any]]:
        """Collect sample data"""
        # This is a placeholder - in a real implementation, this would collect actual content
        sample_data = {
            "type": "statement",
            "content": "This is a sample statement for secure demonstration",
            "source": "secure_sample_source",
            "timestamp": time.time(),
            "context": "Secure sample context information"
        }
        
        return sample_data
        
    def submit_immediately(self, data: Dict[str, Any]) -> bool:
        """Submit data immediately through secure channel"""
        try:
            # Queue for immediate submission
            self.batched_submission.queue_submission(data)
            return True
        except Exception as e:
            print(f"Error in immediate submission: {e}")
            return False
            
    def get_client_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "anonymous_id": self.anonymous_id,
            "is_running": self.is_running,
            "batch_stats": self.batched_submission.get_batch_stats(),
            "routing_stats": self.batched_submission.onion_router.get_routing_stats(),
            "encryption_stats": self.secure_transmission.get_encryption_stats()
        }

# Example usage
if __name__ == "__main__":
    # Initialize secure volunteer client
    client = SecureVolunteerClient("http://localhost:5000")
    
    # Print client stats
    print("Client Stats:", client.get_client_stats())
    
    # Start collection
    client.start_collection()
    
    # Let it run for a bit
    time.sleep(10)
    
    # Submit a single item immediately
    sample_item = {
        "type": "urgent_statement",
        "content": "This is an urgent statement",
        "source": "urgent_source",
        "timestamp": time.time()
    }
    
    client.submit_immediately(sample_item)
    
    # Let it run a bit more
    time.sleep(5)
    
    # Stop collection
    client.stop_collection()
    
    # Print final stats
    print("Final Stats:", client.get_client_stats())