import ipfshttpclient
import json
import time
from verifier import DataVerifier
import threading
import queue

class IPFSMonitor:
    def __init__(self, topic="lodestar.new_content", cache_size=1000):
        """Initialize IPFS monitor with pubsub topic"""
        self.topic = topic
        self.cache_size = cache_size
        self.processed_hashes = set()
        self.verification_queue = queue.Queue()
        self.verifier = DataVerifier()
        self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        self.running = False
        
    def start_monitoring(self):
        """Start monitoring IPFS pubsub for new content"""
        self.running = True
        
        # Start verification worker thread
        verification_thread = threading.Thread(target=self._verification_worker)
        verification_thread.daemon = True
        verification_thread.start()
        
        print(f"Starting IPFS monitor on topic: {self.topic}")
        
        # Subscribe to pubsub topic
        try:
            with self.ipfs_client.pubsub.subscribe(self.topic) as subscription:
                for message in subscription:
                    if not self.running:
                        break
                        
                    try:
                        # Parse message data
                        data = json.loads(message['data'].decode('utf-8'))
                        ipfs_hash = data.get('ipfs_hash')
                        
                        if ipfs_hash and ipfs_hash not in self.processed_hashes:
                            print(f"New content detected: {ipfs_hash}")
                            
                            # Add to processed cache
                            self.processed_hashes.add(ipfs_hash)
                            
                            # Limit cache size
                            if len(self.processed_hashes) > self.cache_size:
                                # Remove oldest items (simplified implementation)
                                oldest = next(iter(self.processed_hashes))
                                self.processed_hashes.remove(oldest)
                            
                            # Add to verification queue
                            self.verification_queue.put(ipfs_hash)
                            
                    except json.JSONDecodeError:
                        print("Invalid JSON in pubsub message")
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        
        except Exception as e:
            print(f"Error subscribing to pubsub: {e}")
            
    def stop_monitoring(self):
        """Stop monitoring IPFS pubsub"""
        self.running = False
        print("IPFS monitoring stopped")
        
    def _verification_worker(self):
        """Worker thread for verifying content"""
        while self.running:
            try:
                # Get IPFS hash from queue (with timeout)
                ipfs_hash = self.verification_queue.get(timeout=1)
                
                # Verify the content
                is_verified = self.verifier.verify_ipfs_data(ipfs_hash)
                
                if is_verified:
                    print(f"Content verified: {ipfs_hash}")
                    # TODO: Send to WebSocket server for broadcasting
                    self._handle_verified_content(ipfs_hash)
                else:
                    print(f"Content verification failed: {ipfs_hash}")
                
                # Mark task as done
                self.verification_queue.task_done()
                
            except queue.Empty:
                # No items in queue, continue loop
                continue
            except Exception as e:
                print(f"Error in verification worker: {e}")
                
    def _handle_verified_content(self, ipfs_hash):
        """Handle verified content (to be extended)"""
        try:
            # Get content from IPFS
            content = self.ipfs_client.get_json(ipfs_hash)
            
            # TODO: Process and categorize content
            # TODO: Send to WebSocket server
            
            print(f"Verified content processed: {ipfs_hash}")
            
        except Exception as e:
            print(f"Error handling verified content: {e}")

# Example usage
if __name__ == "__main__":
    monitor = IPFSMonitor()
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("Stopping monitor...")
        monitor.stop_monitoring()