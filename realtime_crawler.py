import hashlib
import json
import time
import threading
import asyncio
import websockets
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RealtimeCrawlTask:
    id: str
    source_type: str  # 'youtube', 'twitter', 'brave_search', 'generic'
    url: str
    priority: str  # 'high', 'medium', 'low'
    submitted_at: float
    deadline: Optional[float]
    continuous: bool  # Whether to continuously monitor this source
    monitoring_interval: int  # Seconds between checks for continuous tasks
    last_crawled: Optional[float] = None
    status: str = 'pending'  # 'pending', 'crawling', 'completed', 'failed'
    result: Optional[Dict[str, Any]] = None

@dataclass
class RealtimeCrawlEvent:
    event_type: str  # 'new_data', 'update', 'error'
    task_id: str
    data: Dict[str, Any]
    timestamp: float
    source_crawler: str

class RealtimeCrawler:
    def __init__(self, websocket_port: int = 8766, max_concurrent_tasks: int = 10):
        """Initialize real-time crawler"""
        self.websocket_port = websocket_port
        self.max_concurrent_tasks = max_concurrent_tasks
        self.crawl_tasks = {}  # task_id -> RealtimeCrawlTask
        self.continuous_tasks = {}  # task_id -> RealtimeCrawlTask (for continuous monitoring)
        self.event_queue = queue.Queue()  # Queue for crawl events
        self.websocket_server = None
        self.websocket_clients = set()  # Set of connected WebSocket clients
        self.is_running = False
        self.crawling_thread = None
        self.monitoring_thread = None
        self.event_thread = None
        self.websocket_thread = None
        
        # Performance metrics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'events_generated': 0,
            'connected_clients': 0
        }
        
        # Locks for thread safety
        self.tasks_lock = threading.Lock()
        self.continuous_lock = threading.Lock()
        self.clients_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
    def start_crawler(self):
        """Start the real-time crawler"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start crawling thread
        self.crawling_thread = threading.Thread(target=self._crawling_loop, daemon=True)
        self.crawling_thread.start()
        
        # Start monitoring thread for continuous tasks
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Start event processing thread
        self.event_thread = threading.Thread(target=self._event_processing_loop, daemon=True)
        self.event_thread.start()
        
        # Start WebSocket server
        self.websocket_thread = threading.Thread(target=self._start_websocket_server, daemon=True)
        self.websocket_thread.start()
        
        logger.info("Real-time crawler started")
        
    def stop_crawler(self):
        """Stop the real-time crawler"""
        self.is_running = False
        
        # Close WebSocket connections
        if self.websocket_server:
            # In a real implementation, we would close the server properly
            pass
            
        # Wait for threads to finish
        if self.crawling_thread:
            self.crawling_thread.join(timeout=5)
            
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
            
        if self.event_thread:
            self.event_thread.join(timeout=5)
            
        if self.websocket_thread:
            self.websocket_thread.join(timeout=5)
            
        logger.info("Real-time crawler stopped")
        
    def submit_crawl_task(self, source_type: str, url: str, priority: str = 'medium',
                         continuous: bool = False, monitoring_interval: int = 300,
                         deadline: Optional[float] = None) -> str:
        """Submit a real-time crawl task"""
        # Generate task ID
        task_id = hashlib.sha256(f"{source_type}:{url}:{time.time()}".encode()).hexdigest()[:16]
        
        # Create task
        task = RealtimeCrawlTask(
            id=task_id,
            source_type=source_type,
            url=url,
            priority=priority,
            submitted_at=time.time(),
            deadline=deadline,
            continuous=continuous,
            monitoring_interval=monitoring_interval
        )
        
        # Add to appropriate queue
        with self.tasks_lock:
            self.crawl_tasks[task_id] = task
            self.stats['total_tasks'] += 1
            
            # If continuous, also add to continuous tasks
            if continuous:
                with self.continuous_lock:
                    self.continuous_tasks[task_id] = task
                    
        logger.info(f"Real-time crawl task {task_id} submitted for {source_type}: {url}")
        return task_id
        
    def _crawling_loop(self):
        """Main crawling loop"""
        while self.is_running:
            try:
                # Get pending tasks
                pending_tasks = self._get_pending_tasks()
                
                # Process tasks up to max concurrent limit
                active_task_count = self._get_active_task_count()
                available_slots = self.max_concurrent_tasks - active_task_count
                
                for task in pending_tasks[:available_slots]:
                    # Start crawling in separate thread
                    crawl_thread = threading.Thread(target=self._execute_crawl_task, args=(task,), daemon=True)
                    crawl_thread.start()
                    
                    # Update task status
                    with self.tasks_lock:
                        task.status = 'crawling'
                        
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in crawling loop: {e}")
                time.sleep(5)
                
    def _get_pending_tasks(self) -> List[RealtimeCrawlTask]:
        """Get list of pending crawl tasks"""
        with self.tasks_lock:
            return [
                task for task in self.crawl_tasks.values()
                if task.status == 'pending'
            ]
            
    def _get_active_task_count(self) -> int:
        """Get count of active crawling tasks"""
        with self.tasks_lock:
            return len([
                task for task in self.crawl_tasks.values()
                if task.status == 'crawling'
            ])
            
    def _execute_crawl_task(self, task: RealtimeCrawlTask):
        """Execute crawl task"""
        start_time = time.time()
        
        try:
            logger.info(f"Crawling {task.url} (task {task.id})")
            
            # Perform crawling based on source type
            crawl_result = self._perform_crawling(task)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update task
            with self.tasks_lock:
                task.status = 'completed'
                task.result = crawl_result
                task.last_crawled = time.time()
                
            # Update statistics
            with self.stats_lock:
                self.stats['completed_tasks'] += 1
                
            # Generate event
            event = RealtimeCrawlEvent(
                event_type='new_data',
                task_id=task.id,
                data=crawl_result,
                timestamp=time.time(),
                source_crawler='local'
            )
            self.event_queue.put(event)
            
            logger.info(f"Task {task.id} completed in {processing_time:.2f} seconds")
            
            # If continuous task, reset status for next crawl
            if task.continuous:
                with self.tasks_lock:
                    task.status = 'pending'  # Ready for next crawl
                    
        except Exception as e:
            # Handle task failure
            processing_time = time.time() - start_time
            
            with self.tasks_lock:
                task.status = 'failed'
                task.result = {'error': str(e)}
                
            # Update statistics
            with self.stats_lock:
                self.stats['failed_tasks'] += 1
                
            # Generate error event
            event = RealtimeCrawlEvent(
                event_type='error',
                task_id=task.id,
                data={'error': str(e)},
                timestamp=time.time(),
                source_crawler='local'
            )
            self.event_queue.put(event)
            
            logger.error(f"Task {task.id} failed after {processing_time:.2f} seconds: {e}")
            
    def _perform_crawling(self, task: RealtimeCrawlTask) -> Dict[str, Any]:
        """Perform actual crawling based on source type"""
        # This is a simplified implementation
        # In a real system, this would use the existing crawler logic
        
        # Simulate different crawling times based on source type
        if task.source_type == 'youtube':
            time.sleep(2)  # YouTube crawling takes longer
        elif task.source_type == 'twitter':
            time.sleep(1)  # Twitter crawling is faster
        else:
            time.sleep(0.5)  # Generic crawling is fastest
            
        # Simulate crawled data
        crawled_data = {
            'url': task.url,
            'source_type': task.source_type,
            'content': f"Real-time content from {task.source_type}",
            'timestamp': time.time(),
            'metadata': {
                'title': f"Real-time title for {task.url}",
                'description': f"Real-time description for {task.source_type} content",
                'author': 'Real-time Author'
            }
        }
        
        return crawled_data
        
    def _monitoring_loop(self):
        """Monitor continuous tasks"""
        while self.is_running:
            try:
                # Get continuous tasks
                continuous_tasks = self._get_continuous_tasks()
                
                current_time = time.time()
                
                # Check which tasks need to be crawled again
                for task in continuous_tasks:
                    # Check if enough time has passed since last crawl
                    if (task.last_crawled is None or 
                        (current_time - task.last_crawled) >= task.monitoring_interval):
                        # Mark task as pending for crawling
                        with self.tasks_lock:
                            if task.id in self.crawl_tasks:
                                self.crawl_tasks[task.id].status = 'pending'
                                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
                
    def _get_continuous_tasks(self) -> List[RealtimeCrawlTask]:
        """Get list of continuous crawl tasks"""
        with self.continuous_lock:
            return list(self.continuous_tasks.values())
            
    def _event_processing_loop(self):
        """Process crawl events and broadcast to WebSocket clients"""
        while self.is_running:
            try:
                # Get event from queue (with timeout)
                try:
                    event = self.event_queue.get(timeout=1)
                except queue.Empty:
                    continue
                    
                # Process event
                self._process_crawl_event(event)
                
                # Mark event as processed
                self.event_queue.task_done()
                
                # Update statistics
                with self.stats_lock:
                    self.stats['events_generated'] += 1
                    
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                
    def _process_crawl_event(self, event: RealtimeCrawlEvent):
        """Process crawl event and broadcast to clients"""
        # Convert event to JSON for broadcasting
        event_json = json.dumps({
            'event_type': event.event_type,
            'task_id': event.task_id,
            'data': event.data,
            'timestamp': event.timestamp,
            'source_crawler': event.source_crawler
        })
        
        # Broadcast to all connected clients
        self._broadcast_to_clients(event_json)
        
    def _broadcast_to_clients(self, message: str):
        """Broadcast message to all connected WebSocket clients"""
        # In a real implementation, we would send to all connected clients
        # This is a simplified version for demonstration
        pass
        
    def _start_websocket_server(self):
        """Start WebSocket server for real-time data streaming"""
        async def websocket_handler(websocket, path):
            # Add client to connected clients
            with self.clients_lock:
                self.websocket_clients.add(websocket)
                with self.stats_lock:
                    self.stats['connected_clients'] = len(self.websocket_clients)
                    
            logger.info(f"New WebSocket client connected. Total clients: {len(self.websocket_clients)}")
            
            try:
                # Keep connection alive
                async for message in websocket:
                    # Handle incoming messages from clients (if needed)
                    pass
                    
            except websockets.exceptions.ConnectionClosed:
                logger.info("WebSocket client disconnected")
            finally:
                # Remove client from connected clients
                with self.clients_lock:
                    self.websocket_clients.discard(websocket)
                    with self.stats_lock:
                        self.stats['connected_clients'] = len(self.websocket_clients)
                        
        # Start WebSocket server
        async def start_server():
            self.websocket_server = await websockets.serve(
                websocket_handler,
                "localhost",
                self.websocket_port
            )
            logger.info(f"WebSocket server started on port {self.websocket_port}")
            await self.websocket_server.wait_closed()
            
        # Run the server
        try:
            asyncio.run(start_server())
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")
            
    def get_crawler_stats(self) -> Dict[str, Any]:
        """Get crawler statistics"""
        with self.stats_lock:
            total = self.stats['total_tasks']
            success_rate = (
                self.stats['completed_tasks'] / total * 100
                if total > 0 else 0
            )
            
            return {
                **self.stats,
                'success_rate': round(success_rate, 2),
                'pending_tasks': len(self._get_pending_tasks()),
                'continuous_tasks': len(self._get_continuous_tasks())
            }
            
    def get_task_info(self, task_id: str) -> Optional[RealtimeCrawlTask]:
        """Get information about a specific task"""
        with self.tasks_lock:
            return self.crawl_tasks.get(task_id)
            
    def get_all_tasks(self) -> Dict[str, RealtimeCrawlTask]:
        """Get information about all tasks"""
        with self.tasks_lock:
            return self.crawl_tasks.copy()
            
    def cancel_crawl_task(self, task_id: str) -> bool:
        """Cancel a crawl task"""
        with self.tasks_lock:
            if task_id in self.crawl_tasks:
                task = self.crawl_tasks[task_id]
                if task.status == 'pending':
                    task.status = 'cancelled'
                    return True
                elif task.status == 'crawling':
                    # In a real implementation, we would try to stop the crawling process
                    task.status = 'cancelling'
                    return True
                    
        return False
        
    def add_event_listener(self, event_type: str, callback: Callable):
        """Add event listener for specific event types"""
        # In a real implementation, we would store callbacks for event types
        # This is a simplified version for demonstration
        pass

# Example usage
if __name__ == "__main__":
    # Initialize real-time crawler
    crawler = RealtimeCrawler()
    
    # Start crawler
    crawler.start_crawler()
    
    # Submit sample real-time crawl tasks
    task_id1 = crawler.submit_crawl_task("twitter", "https://twitter.com/sample_user", "high", continuous=True, monitoring_interval=60)
    task_id2 = crawler.submit_crawl_task("youtube", "https://youtube.com/sample_video", "medium")
    
    print(f"Submitted real-time crawl tasks: {task_id1}, {task_id2}")
    
    # Wait for tasks to process
    time.sleep(10)
    
    # Get crawler stats
    stats = crawler.get_crawler_stats()
    print(f"Crawler stats: {stats}")
    
    # Stop crawler
    crawler.stop_crawler()