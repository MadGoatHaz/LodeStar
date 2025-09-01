import hashlib
import json
import time
import threading
import asyncio
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CrawlTask:
    id: str
    source_type: str  # 'youtube', 'twitter', 'brave_search', 'generic'
    url: str
    priority: str  # 'high', 'medium', 'low'
    submitted_at: float
    deadline: Optional[float]
    assigned_crawler: Optional[str] = None  # crawler_id
    status: str = 'pending'  # 'pending', 'assigned', 'crawling', 'completed', 'failed'
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0

@dataclass
class CrawlerNode:
    id: str
    address: str
    port: int
    status: str  # 'active', 'inactive', 'busy'
    last_heartbeat: float
    capabilities: List[str]  # List of source types this crawler can handle
    performance_metrics: Dict[str, Any]
    current_load: int  # Number of active tasks

@dataclass
class CrawlResult:
    task_id: str
    data: Dict[str, Any]
    crawler_id: str
    crawled_at: float
    processing_time: float
    verified: bool = False

class DistributedCrawler:
    def __init__(self, max_retries: int = 3, default_timeout: int = 300):
        """Initialize distributed crawler"""
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self.crawl_tasks = {}  # task_id -> CrawlTask
        self.crawler_nodes = {}  # crawler_id -> CrawlerNode
        self.task_queue = []  # List of unassigned tasks
        self.crawl_results = {}  # task_id -> CrawlResult
        self.is_running = False
        self.assignment_thread = None
        self.monitoring_thread = None
        self.heartbeat_interval = 30  # seconds
        
        # Performance metrics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_crawlers': 0
        }
        
        # Locks for thread safety
        self.tasks_lock = threading.Lock()
        self.crawlers_lock = threading.Lock()
        self.results_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
    def start_crawler(self):
        """Start the distributed crawler"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start assignment thread
        self.assignment_thread = threading.Thread(target=self._assignment_loop, daemon=True)
        self.assignment_thread.start()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Distributed crawler started")
        
    def stop_crawler(self):
        """Stop the distributed crawler"""
        self.is_running = False
        
        if self.assignment_thread:
            self.assignment_thread.join(timeout=5)
            
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
            
        logger.info("Distributed crawler stopped")
        
    def register_crawler(self, crawler_id: str, address: str, port: int, capabilities: List[str]):
        """Register a crawler node"""
        crawler = CrawlerNode(
            id=crawler_id,
            address=address,
            port=port,
            status='active',
            last_heartbeat=time.time(),
            capabilities=capabilities,
            performance_metrics={},
            current_load=0
        )
        
        with self.crawlers_lock:
            self.crawler_nodes[crawler_id] = crawler
            self.stats['active_crawlers'] = len([c for c in self.crawler_nodes.values() if c.status == 'active'])
            
        logger.info(f"Crawler {crawler_id} registered with capabilities: {capabilities}")
        
    def submit_crawl_task(self, source_type: str, url: str, priority: str = 'medium',
                         deadline: Optional[float] = None) -> str:
        """Submit a crawl task to the distributed crawler"""
        # Generate task ID
        task_id = hashlib.sha256(f"{source_type}:{url}:{time.time()}:{random.random()}".encode()).hexdigest()[:16]
        
        # Create task
        task = CrawlTask(
            id=task_id,
            source_type=source_type,
            url=url,
            priority=priority,
            submitted_at=time.time(),
            deadline=deadline or (time.time() + self.default_timeout)
        )
        
        # Add to task queue
        with self.tasks_lock:
            self.crawl_tasks[task_id] = task
            self.task_queue.append(task)
            self.stats['total_tasks'] += 1
            
        logger.info(f"Crawl task {task_id} submitted for {source_type}: {url}")
        return task_id
        
    def _assignment_loop(self):
        """Main task assignment loop"""
        while self.is_running:
            try:
                # Process tasks in queue
                if self.task_queue:
                    self._assign_tasks()
                    
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in assignment loop: {e}")
                time.sleep(5)
                
    def _assign_tasks(self):
        """Assign tasks to available crawlers"""
        # Sort tasks by priority
        self.task_queue.sort(key=lambda x: {'high': 1, 'medium': 2, 'low': 3}.get(x.priority, 2))
        
        for task in self.task_queue[:]:  # Copy to avoid modification during iteration
            # Check if task has expired
            if task.deadline and time.time() > task.deadline:
                self._handle_task_timeout(task)
                continue
                
            # Select crawler based on source type and capabilities
            crawler = self._select_crawler(task)
            
            if crawler:
                # Assign task to crawler
                success = self._assign_task_to_crawler(task, crawler)
                if success:
                    self.task_queue.remove(task)
                    
    def _select_crawler(self, task: CrawlTask) -> Optional[CrawlerNode]:
        """Select the best crawler for a task"""
        available_crawlers = self._get_available_crawlers()
        
        if not available_crawlers:
            return None
            
        # Filter crawlers by capabilities
        capable_crawlers = [
            c for c in available_crawlers 
            if task.source_type in c.capabilities or task.source_type == 'generic'
        ]
        
        if not capable_crawlers:
            return None
            
        # Select crawler based on performance and load
        return self._select_best_crawler(capable_crawlers)
        
    def _get_available_crawlers(self) -> List[CrawlerNode]:
        """Get list of available crawlers"""
        with self.crawlers_lock:
            return [
                crawler for crawler in self.crawler_nodes.values()
                if crawler.status == 'active'
            ]
            
    def _select_best_crawler(self, crawlers: List[CrawlerNode]) -> Optional[CrawlerNode]:
        """Select the best crawler based on performance and load"""
        if not crawlers:
            return None
            
        # Score crawlers based on performance and load
        scored_crawlers = []
        for crawler in crawlers:
            # Performance score (0-1) minus load factor (0-0.5)
            load_factor = min(0.5, crawler.current_load / 10.0)  # Assume max 10 tasks per crawler
            performance_score = crawler.performance_metrics.get('success_rate', 0.8)
            score = performance_score - load_factor
            scored_crawlers.append((crawler, score))
            
        # Sort by score (highest first)
        scored_crawlers.sort(key=lambda x: x[1], reverse=True)
        
        return scored_crawlers[0][0] if scored_crawlers else None
        
    def _assign_task_to_crawler(self, task: CrawlTask, crawler: CrawlerNode) -> bool:
        """Assign task to a specific crawler"""
        try:
            with self.tasks_lock:
                task.assigned_crawler = crawler.id
                task.status = 'assigned'
                
            # In a real implementation, we would send the task to the crawler node
            # For now, we'll simulate the crawling process
            logger.info(f"Task {task.id} assigned to crawler {crawler.id}")
            
            # Update crawler load
            with self.crawlers_lock:
                if crawler.id in self.crawler_nodes:
                    self.crawler_nodes[crawler.id].current_load += 1
                    
            # Start crawling in a separate thread
            crawl_thread = threading.Thread(target=self._execute_crawl_task, args=(task, crawler), daemon=True)
            crawl_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error assigning task {task.id} to crawler {crawler.id}: {e}")
            return False
            
    def _execute_crawl_task(self, task: CrawlTask, crawler: CrawlerNode):
        """Execute crawl task (simulated)"""
        start_time = time.time()
        
        try:
            with self.tasks_lock:
                task.status = 'crawling'
                
            logger.info(f"Crawling {task.url} with crawler {crawler.id}")
            
            # Simulate crawling process
            crawl_result = self._simulate_crawling(task)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Store result
            with self.results_lock:
                self.crawl_results[task.id] = CrawlResult(
                    task_id=task.id,
                    data=crawl_result,
                    crawler_id=crawler.id,
                    crawled_at=time.time(),
                    processing_time=processing_time,
                    verified=False
                )
                
            # Update task status
            with self.tasks_lock:
                task.status = 'completed'
                task.result = crawl_result
                
            # Update statistics
            with self.stats_lock:
                self.stats['completed_tasks'] += 1
                
            logger.info(f"Task {task.id} completed by crawler {crawler.id} in {processing_time:.2f} seconds")
            
            # Update crawler load
            with self.crawlers_lock:
                if crawler.id in self.crawler_nodes:
                    self.crawler_nodes[crawler.id].current_load = max(0, self.crawler_nodes[crawler.id].current_load - 1)
                    
        except Exception as e:
            # Handle task failure
            processing_time = time.time() - start_time
            
            with self.tasks_lock:
                task.status = 'failed'
                task.result = {'error': str(e)}
                
            # Update statistics
            with self.stats_lock:
                self.stats['failed_tasks'] += 1
                
            logger.error(f"Task {task.id} failed after {processing_time:.2f} seconds: {e}")
            
            # Update crawler load
            with self.crawlers_lock:
                if crawler.id in self.crawler_nodes:
                    self.crawler_nodes[crawler.id].current_load = max(0, self.crawler_nodes[crawler.id].current_load - 1)
                    
            # Try to retry task
            if task.retry_count < self.max_retries:
                self._retry_task(task)
                
    def _simulate_crawling(self, task: CrawlTask) -> Dict[str, Any]:
        """Simulate crawling process"""
        # This is a placeholder for the actual crawling implementation
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
            'content': f"Sample content from {task.source_type}",
            'timestamp': time.time(),
            'metadata': {
                'title': f"Sample title for {task.url}",
                'description': f"Sample description for {task.source_type} content",
                'author': 'Sample Author'
            }
        }
        
        return crawled_data
        
    def _handle_task_timeout(self, task: CrawlTask):
        """Handle task timeout"""
        logger.warning(f"Task {task.id} timed out")
        
        with self.tasks_lock:
            task.status = 'failed'
            task.result = {'error': 'Task timed out'}
            
        with self.stats_lock:
            self.stats['failed_tasks'] += 1
            
        # Try to reassign if retries available
        if task.retry_count < self.max_retries:
            self._retry_task(task)
            
    def _retry_task(self, task: CrawlTask):
        """Retry a failed task"""
        with self.tasks_lock:
            task.retry_count += 1
            task.status = 'pending'
            task.assigned_crawler = None
            self.task_queue.append(task)
            
        logger.info(f"Task {task.id} retried (attempt {task.retry_count})")
        
    def _monitoring_loop(self):
        """Monitor crawler nodes and task progress"""
        while self.is_running:
            try:
                # Update crawler status
                self._update_crawler_status()
                
                # Check task progress
                self._check_task_progress()
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
                
    def _update_crawler_status(self):
        """Update status of crawler nodes"""
        with self.crawlers_lock:
            current_time = time.time()
            for crawler_id, crawler in self.crawler_nodes.items():
                # Check if crawler is inactive (no heartbeat for 2 minutes)
                if current_time - crawler.last_heartbeat > 120:
                    crawler.status = 'inactive'
                    
            self.stats['active_crawlers'] = len([c for c in self.crawler_nodes.values() if c.status == 'active'])
            
    def _check_task_progress(self):
        """Check progress of assigned tasks"""
        with self.tasks_lock:
            current_time = time.time()
            for task_id, task in self.crawl_tasks.items():
                if task.status == 'assigned' or task.status == 'crawling':
                    # Check if task has timed out
                    if task.deadline and current_time > task.deadline:
                        self._handle_task_timeout(task)
                    # Check if task has exceeded retry limit
                    elif task.retry_count >= self.max_retries:
                        self._handle_task_failure(task)
                        
    def _handle_task_failure(self, task: CrawlTask):
        """Handle task failure after max retries"""
        logger.error(f"Task {task.id} failed after {self.max_retries} retries")
        
        with self.tasks_lock:
            task.status = 'failed'
            if not task.result:
                task.result = {'error': 'Task failed after maximum retries'}
                
        with self.stats_lock:
            self.stats['failed_tasks'] += 1
            
    def get_crawl_result(self, task_id: str) -> Optional[CrawlResult]:
        """Get result for a crawl task"""
        with self.results_lock:
            return self.crawl_results.get(task_id)
            
    def get_crawler_stats(self) -> Dict[str, Any]:
        """Get crawler statistics"""
        with self.stats_lock:
            total = self.stats['total_tasks']
            success_rate = (
                self.stats['completed_tasks'] / total * 100
                if total > 0 else 0
            )
            
            with self.crawlers_lock:
                self.stats['active_crawlers'] = len([c for c in self.crawler_nodes.values() if c.status == 'active'])
                
            return {
                **self.stats,
                'success_rate': round(success_rate, 2),
                'queue_size': len(self.task_queue)
            }
            
    def get_crawler_info(self, crawler_id: str) -> Optional[CrawlerNode]:
        """Get information about a specific crawler"""
        with self.crawlers_lock:
            return self.crawler_nodes.get(crawler_id)
            
    def get_all_crawlers(self) -> Dict[str, CrawlerNode]:
        """Get information about all crawlers"""
        with self.crawlers_lock:
            return self.crawler_nodes.copy()
            
    def update_crawler_heartbeat(self, crawler_id: str, metrics: Dict[str, Any] = None):
        """Update crawler heartbeat"""
        with self.crawlers_lock:
            if crawler_id in self.crawler_nodes:
                self.crawler_nodes[crawler_id].last_heartbeat = time.time()
                self.crawler_nodes[crawler_id].status = 'active'
                if metrics:
                    self.crawler_nodes[crawler_id].performance_metrics = metrics
                    
    def cancel_crawl_task(self, task_id: str) -> bool:
        """Cancel a pending crawl task"""
        with self.tasks_lock:
            if task_id in self.crawl_tasks:
                task = self.crawl_tasks[task_id]
                if task.status == 'pending':
                    # Remove from queue if present
                    if task in self.task_queue:
                        self.task_queue.remove(task)
                    # Update status
                    task.status = 'cancelled'
                    return True
        return False

# Example usage
if __name__ == "__main__":
    # Initialize distributed crawler
    crawler = DistributedCrawler()
    
    # Start crawler
    crawler.start_crawler()
    
    # Register sample crawlers
    crawler.register_crawler("crawler_1", "127.0.0.1", 8001, ["youtube", "twitter"])
    crawler.register_crawler("crawler_2", "127.0.0.1", 8002, ["brave_search", "generic"])
    
    # Submit sample crawl tasks
    task_id1 = crawler.submit_crawl_task("youtube", "https://youtube.com/sample_video", "high")
    task_id2 = crawler.submit_crawl_task("twitter", "https://twitter.com/sample_user", "medium")
    task_id3 = crawler.submit_crawl_task("brave_search", "https://search.brave.com/search?q=sample", "low")
    
    print(f"Submitted crawl tasks: {task_id1}, {task_id2}, {task_id3}")
    
    # Wait for tasks to complete
    time.sleep(10)
    
    # Check task results
    result1 = crawler.get_crawl_result(task_id1)
    result2 = crawler.get_crawl_result(task_id2)
    result3 = crawler.get_crawl_result(task_id3)
    
    if result1:
        print(f"Task 1 result: {result1.data.get('content', 'No content')}")
    if result2:
        print(f"Task 2 result: {result2.data.get('content', 'No content')}")
    if result3:
        print(f"Task 3 result: {result3.data.get('content', 'No content')}")
        
    # Get crawler stats
    stats = crawler.get_crawler_stats()
    print(f"Crawler stats: {stats}")
    
    # Stop crawler
    crawler.stop_crawler()