import hashlib
import json
import time
import threading
import base64
import random
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from typing import Dict, List, Any, Optional
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VolunteerCrawler:
    def __init__(self, coordinator_url: str = "http://localhost:5000", crawler_id: str = None):
        """Initialize volunteer crawler"""
        self.coordinator_url = coordinator_url
        self.crawler_id = crawler_id or self._generate_crawler_id()
        self.private_key = None
        self.public_key = None
        self.is_running = False
        self.heartbeat_thread = None
        self.task_thread = None
        self.current_task = None
        self.task_capabilities = ["youtube", "twitter", "brave_search", "generic"]
        self.heartbeat_interval = 30  # seconds
        self.reputation_score = 1.0  # Start with neutral reputation
        
        # Generate key pair for signing submissions
        self._generate_key_pair()
        
        # Performance metrics
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'data_submitted': 0
        }
        
        # Locks for thread safety
        self.stats_lock = threading.Lock()
        
    def _generate_crawler_id(self) -> str:
        """Generate unique crawler ID"""
        return hashlib.sha256(f"volunteer_crawler:{time.time()}:{random.random()}".encode()).hexdigest()[:16]
        
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
        
    def start_crawler(self):
        """Start the volunteer crawler"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Register with coordinator
        if not self._register_with_coordinator():
            logger.error("Failed to register with coordinator")
            return
            
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        # Start task processing thread
        self.task_thread = threading.Thread(target=self._task_processing_loop, daemon=True)
        self.task_thread.start()
        
        logger.info(f"Volunteer crawler {self.crawler_id} started")
        
    def stop_crawler(self):
        """Stop the volunteer crawler"""
        self.is_running = False
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
            
        if self.task_thread:
            self.task_thread.join(timeout=5)
            
        logger.info(f"Volunteer crawler {self.crawler_id} stopped")
        
    def _register_with_coordinator(self) -> bool:
        """Register with the coordinator"""
        try:
            registration_data = {
                "crawler_id": self.crawler_id,
                "capabilities": self.task_capabilities,
                "public_key": self.get_public_key_pem(),
                "timestamp": time.time()
            }
            
            response = requests.post(
                f"{self.coordinator_url}/api/crawlers/register",
                json=registration_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully registered with coordinator")
                return True
            else:
                logger.error(f"Failed to register with coordinator: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering with coordinator: {e}")
            return False
            
    def _heartbeat_loop(self):
        """Send heartbeats to coordinator"""
        while self.is_running:
            try:
                # Send heartbeat
                self._send_heartbeat()
                
                # Wait for next heartbeat
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(5)
                
    def _send_heartbeat(self):
        """Send heartbeat to coordinator"""
        try:
            heartbeat_data = {
                "crawler_id": self.crawler_id,
                "timestamp": time.time(),
                "stats": self.get_stats(),
                "reputation_score": self.reputation_score
            }
            
            response = requests.post(
                f"{self.coordinator_url}/api/crawlers/heartbeat",
                json=heartbeat_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.warning(f"Heartbeat failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            
    def _task_processing_loop(self):
        """Process tasks from coordinator"""
        while self.is_running:
            try:
                # Request task from coordinator
                task = self._request_task()
                
                if task:
                    # Process task
                    self._process_task(task)
                else:
                    # No task available, wait before retrying
                    time.sleep(10)
                    
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
                time.sleep(5)
                
    def _request_task(self) -> Optional[Dict[str, Any]]:
        """Request task from coordinator"""
        try:
            request_data = {
                "crawler_id": self.crawler_id,
                "capabilities": self.task_capabilities,
                "timestamp": time.time()
            }
            
            response = requests.post(
                f"{self.coordinator_url}/api/crawlers/request_task",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                task_data = response.json()
                if task_data.get("task"):
                    logger.info(f"Received task: {task_data['task']['id']}")
                    return task_data["task"]
                    
            return None
            
        except Exception as e:
            logger.error(f"Error requesting task: {e}")
            return None
            
    def _process_task(self, task: Dict[str, Any]):
        """Process a crawl task"""
        task_id = task.get("id")
        source_type = task.get("source_type")
        url = task.get("url")
        
        try:
            logger.info(f"Processing task {task_id} for {source_type}: {url}")
            
            # Mark task as in progress
            self.current_task = task_id
            
            # Perform crawling based on source type
            crawl_result = self._execute_crawl(source_type, url, task)
            
            # Submit result
            self._submit_result(task_id, crawl_result)
            
            # Update statistics
            with self.stats_lock:
                self.stats['tasks_completed'] += 1
                
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            
            # Submit error result
            error_result = {
                "error": str(e),
                "timestamp": time.time()
            }
            
            self._submit_result(task_id, error_result, success=False)
            
            # Update statistics
            with self.stats_lock:
                self.stats['tasks_failed'] += 1
                
        finally:
            self.current_task = None
            
    def _execute_crawl(self, source_type: str, url: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute crawl based on source type"""
        # This is a simplified implementation
        # In a real system, this would use the existing crawler logic
        
        # Simulate different crawling times based on source type
        if source_type == "youtube":
            time.sleep(2)  # YouTube crawling takes longer
        elif source_type == "twitter":
            time.sleep(1)  # Twitter crawling is faster
        else:
            time.sleep(0.5)  # Generic crawling is fastest
            
        # Simulate crawled data
        crawled_data = {
            "url": url,
            "source_type": source_type,
            "content": f"Sample content from {source_type}",
            "timestamp": time.time(),
            "metadata": {
                "title": f"Sample title for {url}",
                "description": f"Sample description for {source_type} content",
                "author": "Sample Author"
            },
            "task_id": task.get("id"),
            "crawler_id": self.crawler_id
        }
        
        return crawled_data
        
    def _submit_result(self, task_id: str, result_data: Dict[str, Any], success: bool = True):
        """Submit crawl result to coordinator"""
        try:
            # Add signature to result
            signature = self.sign_data(result_data)
            
            submission_data = {
                "task_id": task_id,
                "crawler_id": self.crawler_id,
                "result": result_data,
                "signature": signature,
                "success": success,
                "timestamp": time.time(),
                "public_key": self.get_public_key_pem()
            }
            
            response = requests.post(
                f"{self.coordinator_url}/api/crawlers/submit_result",
                json=submission_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Result for task {task_id} submitted successfully")
                with self.stats_lock:
                    self.stats['data_submitted'] += 1
            else:
                logger.error(f"Failed to submit result for task {task_id}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error submitting result for task {task_id}: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get crawler statistics"""
        with self.stats_lock:
            total_tasks = self.stats['tasks_completed'] + self.stats['tasks_failed']
            success_rate = (
                self.stats['tasks_completed'] / total_tasks * 100
                if total_tasks > 0 else 0
            )
            
            return {
                **self.stats,
                'success_rate': round(success_rate, 2),
                'current_task': self.current_task,
                'reputation_score': self.reputation_score
            }
            
    def update_reputation(self, score_change: float):
        """Update crawler reputation score"""
        self.reputation_score = max(0.0, min(10.0, self.reputation_score + score_change))
        logger.info(f"Reputation score updated to {self.reputation_score}")

# Coordinator-side integration
class CrawlerCoordinator:
    def __init__(self):
        """Initialize crawler coordinator"""
        self.volunteer_crawlers = {}  # crawler_id -> crawler_info
        self.crawler_stats = {}  # crawler_id -> stats
        self.lock = threading.Lock()
        
    def register_crawler(self, registration_data: Dict[str, Any]) -> bool:
        """Register a volunteer crawler"""
        crawler_id = registration_data.get("crawler_id")
        capabilities = registration_data.get("capabilities", [])
        public_key = registration_data.get("public_key")
        
        if not crawler_id or not public_key:
            return False
            
        with self.lock:
            self.volunteer_crawlers[crawler_id] = {
                "id": crawler_id,
                "capabilities": capabilities,
                "public_key": public_key,
                "registered_at": time.time(),
                "last_heartbeat": time.time(),
                "status": "active"
            }
            
        logger.info(f"Volunteer crawler {crawler_id} registered")
        return True
        
    def handle_heartbeat(self, heartbeat_data: Dict[str, Any]) -> bool:
        """Handle heartbeat from volunteer crawler"""
        crawler_id = heartbeat_data.get("crawler_id")
        
        with self.lock:
            if crawler_id in self.volunteer_crawlers:
                self.volunteer_crawlers[crawler_id]["last_heartbeat"] = time.time()
                self.volunteer_crawlers[crawler_id]["status"] = "active"
                self.crawler_stats[crawler_id] = heartbeat_data.get("stats", {})
                return True
                
        return False
        
    def get_available_crawlers(self) -> List[Dict[str, Any]]:
        """Get list of available volunteer crawlers"""
        current_time = time.time()
        available_crawlers = []
        
        with self.lock:
            for crawler_id, crawler_info in self.volunteer_crawlers.items():
                # Check if crawler is active (heartbeat within last 2 minutes)
                if (current_time - crawler_info["last_heartbeat"]) < 120:
                    available_crawlers.append(crawler_info)
                    
        return available_crawlers
        
    def get_crawler_stats(self, crawler_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific crawler"""
        with self.lock:
            return self.crawler_stats.get(crawler_id)

# Example usage
if __name__ == "__main__":
    # Initialize volunteer crawler
    crawler = VolunteerCrawler("http://localhost:5000")
    
    # Start crawler
    crawler.start_crawler()
    
    # Let it run for a bit
    time.sleep(30)
    
    # Get stats
    stats = crawler.get_stats()
    print(f"Crawler stats: {stats}")
    
    # Stop crawler
    crawler.stop_crawler()