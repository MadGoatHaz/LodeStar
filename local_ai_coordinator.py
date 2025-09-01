import hashlib
import json
import time
import threading
import queue
import subprocess
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LocalTask:
    id: str
    type: str  # 'verification', 'analysis', 'processing'
    data: Dict[str, Any]
    priority: str  # 'high', 'medium', 'low'
    submitted_at: float
    deadline: Optional[float]
    status: str  # 'pending', 'processing', 'completed', 'failed'
    result: Optional[Dict[str, Any]] = None
    processing_time: float = 0.0

@dataclass
class ResourceMetrics:
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    disk_usage: float
    network_usage: float

class LocalAICoordinator:
    def __init__(self, max_concurrent_tasks: int = 4, model_path: str = "./models"):
        """Initialize local AI coordinator"""
        self.max_concurrent_tasks = max_concurrent_tasks
        self.model_path = model_path
        self.task_queue = queue.PriorityQueue()  # Priority queue for tasks
        self.active_tasks = {}  # task_id -> LocalTask
        self.completed_tasks = {}  # task_id -> LocalTask
        self.task_workers = []  # List of worker threads
        self.is_running = False
        self.resource_monitor_thread = None
        self.task_timeout = 300  # 5 minutes default timeout
        self.resource_metrics = ResourceMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Performance metrics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'average_processing_time': 0.0
        }
        
        # Locks for thread safety
        self.queue_lock = threading.Lock()
        self.tasks_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
        # Create model directory if it doesn't exist
        if not os.path.exists(model_path):
            os.makedirs(model_path)
            
    def start_coordinator(self):
        """Start the local AI coordinator"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start resource monitoring thread
        self.resource_monitor_thread = threading.Thread(target=self._resource_monitor_loop, daemon=True)
        self.resource_monitor_thread.start()
        
        # Start worker threads
        for i in range(self.max_concurrent_tasks):
            worker = threading.Thread(target=self._worker_loop, daemon=True, name=f"Worker-{i}")
            worker.start()
            self.task_workers.append(worker)
            
        logger.info(f"Local AI coordinator started with {self.max_concurrent_tasks} workers")
        
    def stop_coordinator(self):
        """Stop the local AI coordinator"""
        self.is_running = False
        
        # Wait for workers to finish
        for worker in self.task_workers:
            worker.join(timeout=5)
            
        if self.resource_monitor_thread:
            self.resource_monitor_thread.join(timeout=5)
            
        logger.info("Local AI coordinator stopped")
        
    def submit_task(self, task_type: str, data: Dict[str, Any], priority: str = 'medium', 
                   deadline: Optional[float] = None) -> str:
        """Submit a task to the local AI coordinator"""
        # Generate task ID
        task_id = hashlib.sha256(f"{task_type}:{time.time()}:{hash(str(data))}".encode()).hexdigest()[:16]
        
        # Determine priority value (lower number = higher priority)
        priority_value = {'high': 1, 'medium': 2, 'low': 3}.get(priority, 2)
        
        # Create task
        task = LocalTask(
            id=task_id,
            type=task_type,
            data=data,
            priority=priority,
            submitted_at=time.time(),
            deadline=deadline,
            status='pending'
        )
        
        # Add to task queue
        with self.queue_lock:
            self.task_queue.put((priority_value, task_id, task))
            
        with self.tasks_lock:
            self.active_tasks[task_id] = task
            self.stats['total_tasks'] += 1
            
        logger.info(f"Task {task_id} submitted to local AI coordinator with priority {priority}")
        return task_id
        
    def _worker_loop(self):
        """Main worker loop for processing tasks"""
        while self.is_running:
            try:
                # Get task from queue (blocking)
                priority_value, task_id, task = self.task_queue.get(timeout=1)
                
                # Process task
                self._process_task(task)
                
                # Mark task as done
                self.task_queue.task_done()
                
            except queue.Empty:
                # No tasks available, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(1)
                
    def _process_task(self, task: LocalTask):
        """Process a single task"""
        start_time = time.time()
        
        try:
            # Update task status
            with self.tasks_lock:
                if task.id in self.active_tasks:
                    self.active_tasks[task.id].status = 'processing'
                    
            logger.info(f"Processing task {task.id} of type {task.type}")
            
            # Process based on task type
            result = self._execute_task(task)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update task with result
            with self.tasks_lock:
                if task.id in self.active_tasks:
                    self.active_tasks[task.id].status = 'completed'
                    self.active_tasks[task.id].result = result
                    self.active_tasks[task.id].processing_time = processing_time
                    
                    # Move to completed tasks
                    completed_task = self.active_tasks[task.id]
                    self.completed_tasks[task.id] = completed_task
                    del self.active_tasks[task.id]
                    
            # Update statistics
            with self.stats_lock:
                self.stats['completed_tasks'] += 1
                total_time = self.stats['average_processing_time'] * (self.stats['completed_tasks'] - 1)
                self.stats['average_processing_time'] = (total_time + processing_time) / self.stats['completed_tasks']
                
            logger.info(f"Task {task.id} completed in {processing_time:.2f} seconds")
            
        except Exception as e:
            # Handle task failure
            processing_time = time.time() - start_time
            
            with self.tasks_lock:
                if task.id in self.active_tasks:
                    self.active_tasks[task.id].status = 'failed'
                    self.active_tasks[task.id].result = {'error': str(e)}
                    self.active_tasks[task.id].processing_time = processing_time
                    
                    # Move to completed tasks (failed)
                    completed_task = self.active_tasks[task.id]
                    self.completed_tasks[task.id] = completed_task
                    del self.active_tasks[task.id]
                    
            # Update statistics
            with self.stats_lock:
                self.stats['failed_tasks'] += 1
                
            logger.error(f"Task {task.id} failed after {processing_time:.2f} seconds: {e}")
            
    def _execute_task(self, task: LocalTask) -> Dict[str, Any]:
        """Execute task based on its type"""
        if task.type == 'verification':
            return self._verify_content(task.data)
        elif task.type == 'analysis':
            return self._analyze_content(task.data)
        elif task.type == 'processing':
            return self._process_content(task.data)
        else:
            raise ValueError(f"Unknown task type: {task.type}")
            
    def _verify_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify content using local AI models"""
        # In a real implementation, this would use actual AI models
        # For now, we'll simulate verification
        
        content = data.get('content', '')
        context = data.get('context', '')
        
        # Simple verification logic (simulated)
        verification_result = {
            'verified': True,
            'confidence': 0.95,
            'issues_found': [],
            'timestamp': time.time()
        }
        
        # Simulate processing time
        time.sleep(0.1)
        
        return verification_result
        
    def _analyze_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content using local AI models"""
        # In a real implementation, this would use actual AI models
        # For now, we'll simulate analysis
        
        content = data.get('content', '')
        
        # Simple analysis logic (simulated)
        analysis_result = {
            'sentiment': 'neutral',
            'key_points': ['Point 1', 'Point 2'],
            'entities': ['Entity 1', 'Entity 2'],
            'summary': f'Analysis of content: {content[:100]}...',
            'timestamp': time.time()
        }
        
        # Simulate processing time
        time.sleep(0.2)
        
        return analysis_result
        
    def _process_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process content using local AI models"""
        # In a real implementation, this would use actual AI models
        # For now, we'll simulate processing
        
        content = data.get('content', '')
        
        # Simple processing logic (simulated)
        processed_result = {
            'processed_content': content.upper(),  # Simple transformation
            'word_count': len(content.split()),
            'character_count': len(content),
            'timestamp': time.time()
        }
        
        # Simulate processing time
        time.sleep(0.15)
        
        return processed_result
        
    def _resource_monitor_loop(self):
        """Monitor system resources"""
        while self.is_running:
            try:
                # Get resource metrics
                metrics = self._get_resource_metrics()
                
                # Update stored metrics
                self.resource_metrics = metrics
                
                # Check if resources are constrained
                if self._are_resources_constrained(metrics):
                    logger.warning("System resources are constrained, reducing task load")
                    
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in resource monitor loop: {e}")
                time.sleep(5)
                
    def _get_resource_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics"""
        try:
            # This is a simplified implementation
            # In a real system, you would use libraries like psutil
            
            # Simulate resource usage
            cpu_usage = 25.0 + (50.0 * (len(self.active_tasks) / max(self.max_concurrent_tasks, 1)))
            memory_usage = 30.0 + (40.0 * (len(self.active_tasks) / max(self.max_concurrent_tasks, 1)))
            gpu_usage = 10.0  # Assuming GPU is not heavily used
            disk_usage = 45.0  # Static for now
            network_usage = 5.0 + (10.0 * len(self.active_tasks))
            
            return ResourceMetrics(
                cpu_usage=min(100.0, cpu_usage),
                memory_usage=min(100.0, memory_usage),
                gpu_usage=min(100.0, gpu_usage),
                disk_usage=min(100.0, disk_usage),
                network_usage=min(100.0, network_usage)
            )
            
        except Exception as e:
            logger.error(f"Error getting resource metrics: {e}")
            return ResourceMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
            
    def _are_resources_constrained(self, metrics: ResourceMetrics) -> bool:
        """Check if system resources are constrained"""
        # Define thresholds for constrained resources
        cpu_threshold = 80.0
        memory_threshold = 85.0
        disk_threshold = 90.0
        
        return (
            metrics.cpu_usage > cpu_threshold or
            metrics.memory_usage > memory_threshold or
            metrics.disk_usage > disk_threshold
        )
        
    def get_task_result(self, task_id: str) -> Optional[LocalTask]:
        """Get result for a completed task"""
        with self.tasks_lock:
            # Check completed tasks first
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
                
            # Check active tasks
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]
                
        return None
        
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        with self.stats_lock:
            total = self.stats['total_tasks']
            success_rate = (
                self.stats['completed_tasks'] / total * 100
                if total > 0 else 0
            )
            
            return {
                **self.stats,
                'success_rate': round(success_rate, 2),
                'active_tasks': len(self.active_tasks),
                'queue_size': self.task_queue.qsize(),
                'resource_metrics': {
                    'cpu_usage': self.resource_metrics.cpu_usage,
                    'memory_usage': self.resource_metrics.memory_usage,
                    'gpu_usage': self.resource_metrics.gpu_usage,
                    'disk_usage': self.resource_metrics.disk_usage,
                    'network_usage': self.resource_metrics.network_usage
                }
            }
            
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self.queue_lock:
            # Create a new queue without the task to cancel
            new_queue = queue.PriorityQueue()
            cancelled = False
            
            # This is a simplified approach - in practice, you might need
            # a more sophisticated method to remove specific items from a PriorityQueue
            temp_items = []
            while not self.task_queue.empty():
                try:
                    item = self.task_queue.get_nowait()
                    if item[1] != task_id:  # item[1] is task_id
                        temp_items.append(item)
                    else:
                        cancelled = True
                except queue.Empty:
                    break
                    
            # Put remaining items back in queue
            for item in temp_items:
                new_queue.put(item)
                
            # Replace the old queue
            self.task_queue = new_queue
            
        if cancelled:
            with self.tasks_lock:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                    
            logger.info(f"Task {task_id} cancelled")
            
        return cancelled
        
    def clear_completed_tasks(self, older_than_hours: int = 24):
        """Clear completed tasks older than specified hours"""
        cutoff_time = time.time() - (older_than_hours * 3600)
        
        with self.tasks_lock:
            old_tasks = [
                task_id for task_id, task in self.completed_tasks.items()
                if task.submitted_at < cutoff_time
            ]
            
            for task_id in old_tasks:
                del self.completed_tasks[task_id]
                
        logger.info(f"Cleared {len(old_tasks)} old completed tasks")

# Example usage
if __name__ == "__main__":
    # Initialize local AI coordinator
    coordinator = LocalAICoordinator(max_concurrent_tasks=2)
    
    # Start coordinator
    coordinator.start_coordinator()
    
    # Submit sample tasks
    task_data1 = {
        "content": "This is sample content for verification",
        "context": "Sample context for verification"
    }
    
    task_data2 = {
        "content": "This is sample content for analysis",
        "context": "Sample context for analysis"
    }
    
    task_id1 = coordinator.submit_task("verification", task_data1, "high")
    task_id2 = coordinator.submit_task("analysis", task_data2, "medium")
    
    print(f"Submitted tasks: {task_id1}, {task_id2}")
    
    # Wait for tasks to complete
    time.sleep(3)
    
    # Check task results
    result1 = coordinator.get_task_result(task_id1)
    result2 = coordinator.get_task_result(task_id2)
    
    if result1:
        print(f"Task 1 result: {result1.status}")
    if result2:
        print(f"Task 2 result: {result2.status}")
        
    # Get coordinator stats
    stats = coordinator.get_coordinator_stats()
    print(f"Coordinator stats: {stats}")
    
    # Stop coordinator
    coordinator.stop_coordinator()