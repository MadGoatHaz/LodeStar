import hashlib
import json
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingTask:
    id: str
    type: str  # 'verification', 'analysis', 'processing'
    data: Dict[str, Any]
    priority: str  # 'high', 'medium', 'low'
    submitted_at: float
    deadline: Optional[float]
    processing_mode: str  # 'distributed', 'local', 'hybrid'
    status: str  # 'pending', 'assigned', 'processing', 'completed', 'failed'
    assigned_processor: Optional[str] = None  # node_id or 'local'
    result: Optional[Dict[str, Any]] = None
    processing_time: float = 0.0
    retry_count: int = 0

@dataclass
class ProcessorInfo:
    processor_id: str
    type: str  # 'distributed_node', 'local_ai'
    status: str  # 'available', 'busy', 'offline'
    performance_score: float  # 0.0 to 1.0
    last_updated: float
    capabilities: List[str]
    current_load: int  # Number of active tasks

class HybridProcessingEngine:
    def __init__(self, distributed_network=None, local_ai_coordinator=None):
        """Initialize hybrid processing engine"""
        self.distributed_network = distributed_network
        self.local_ai_coordinator = local_ai_coordinator
        self.tasks = {}  # task_id -> ProcessingTask
        self.processors = {}  # processor_id -> ProcessorInfo
        self.task_queue = []  # List of unassigned tasks
        self.is_running = False
        self.assignment_thread = None
        self.monitoring_thread = None
        self.max_retries = 3
        self.default_timeout = 300  # 5 minutes
        
        # Performance metrics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'distributed_tasks': 0,
            'local_tasks': 0,
            'hybrid_tasks': 0
        }
        
        # Locks for thread safety
        self.tasks_lock = threading.Lock()
        self.processors_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
        # Register local AI processor if available
        if self.local_ai_coordinator:
            self._register_local_processor()
            
    def _register_local_processor(self):
        """Register local AI as a processor"""
        local_processor = ProcessorInfo(
            processor_id='local_ai',
            type='local_ai',
            status='available',
            performance_score=0.8,  # Default score
            last_updated=time.time(),
            capabilities=['verification', 'analysis', 'processing'],
            current_load=0
        )
        
        with self.processors_lock:
            self.processors['local_ai'] = local_processor
            
        logger.info("Local AI processor registered")
        
    def start_engine(self):
        """Start the hybrid processing engine"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start assignment thread
        self.assignment_thread = threading.Thread(target=self._assignment_loop, daemon=True)
        self.assignment_thread.start()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Hybrid processing engine started")
        
    def stop_engine(self):
        """Stop the hybrid processing engine"""
        self.is_running = False
        
        if self.assignment_thread:
            self.assignment_thread.join(timeout=5)
            
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
            
        logger.info("Hybrid processing engine stopped")
        
    def submit_task(self, task_type: str, data: Dict[str, Any], priority: str = 'medium',
                   deadline: Optional[float] = None, processing_mode: str = 'hybrid') -> str:
        """Submit a task to the hybrid processing engine"""
        # Generate task ID
        task_id = hashlib.sha256(f"{task_type}:{time.time()}:{random.random()}".encode()).hexdigest()[:16]
        
        # Create task
        task = ProcessingTask(
            id=task_id,
            type=task_type,
            data=data,
            priority=priority,
            submitted_at=time.time(),
            deadline=deadline or (time.time() + self.default_timeout),
            processing_mode=processing_mode,
            status='pending'
        )
        
        # Add to task queue
        with self.tasks_lock:
            self.tasks[task_id] = task
            self.task_queue.append(task)
            self.stats['total_tasks'] += 1
            
            # Update stats based on processing mode
            if processing_mode == 'distributed':
                self.stats['distributed_tasks'] += 1
            elif processing_mode == 'local':
                self.stats['local_tasks'] += 1
            elif processing_mode == 'hybrid':
                self.stats['hybrid_tasks'] += 1
                
        logger.info(f"Task {task_id} submitted with mode {processing_mode}")
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
        """Assign tasks to available processors"""
        # Sort tasks by priority
        self.task_queue.sort(key=lambda x: {'high': 1, 'medium': 2, 'low': 3}.get(x.priority, 2))
        
        for task in self.task_queue[:]:  # Copy to avoid modification during iteration
            # Check if task has expired
            if task.deadline and time.time() > task.deadline:
                self._handle_task_timeout(task)
                continue
                
            # Select processor based on processing mode
            processor = self._select_processor(task)
            
            if processor:
                # Assign task to processor
                success = self._assign_task_to_processor(task, processor)
                if success:
                    self.task_queue.remove(task)
                    
    def _select_processor(self, task: ProcessingTask) -> Optional[ProcessorInfo]:
        """Select the best processor for a task"""
        available_processors = self._get_available_processors()
        
        if not available_processors:
            return None
            
        # Filter processors by capabilities
        capable_processors = [
            p for p in available_processors 
            if task.type in p.capabilities or not task.type
        ]
        
        if not capable_processors:
            return None
            
        # Select processor based on processing mode
        if task.processing_mode == 'distributed':
            # Prefer distributed nodes
            distributed_processors = [p for p in capable_processors if p.type == 'distributed_node']
            if distributed_processors:
                return self._select_best_processor(distributed_processors)
            # Fallback to local if no distributed nodes available
            local_processors = [p for p in capable_processors if p.type == 'local_ai']
            return local_processors[0] if local_processors else None
            
        elif task.processing_mode == 'local':
            # Prefer local AI
            local_processors = [p for p in capable_processors if p.type == 'local_ai']
            return local_processors[0] if local_processors else None
            
        else:  # hybrid mode
            # Select based on performance and load
            return self._select_best_processor(capable_processors)
            
    def _get_available_processors(self) -> List[ProcessorInfo]:
        """Get list of available processors"""
        with self.processors_lock:
            return [
                processor for processor in self.processors.values()
                if processor.status == 'available'
            ]
            
    def _select_best_processor(self, processors: List[ProcessorInfo]) -> Optional[ProcessorInfo]:
        """Select the best processor based on performance and load"""
        if not processors:
            return None
            
        # Score processors based on performance and load
        scored_processors = []
        for processor in processors:
            # Performance score (0-1) minus load factor (0-0.5)
            load_factor = min(0.5, processor.current_load / 10.0)  # Assume max 10 tasks per processor
            score = processor.performance_score - load_factor
            scored_processors.append((processor, score))
            
        # Sort by score (highest first)
        scored_processors.sort(key=lambda x: x[1], reverse=True)
        
        return scored_processors[0][0] if scored_processors else None
        
    def _assign_task_to_processor(self, task: ProcessingTask, processor: ProcessorInfo) -> bool:
        """Assign task to a specific processor"""
        try:
            with self.tasks_lock:
                task.assigned_processor = processor.processor_id
                task.status = 'assigned'
                
            # Assign based on processor type
            if processor.type == 'distributed_node' and self.distributed_network:
                # Assign to distributed network
                success = self._assign_to_distributed_network(task, processor)
            elif processor.type == 'local_ai' and self.local_ai_coordinator:
                # Assign to local AI
                success = self._assign_to_local_ai(task, processor)
            else:
                success = False
                
            if success:
                # Update processor load
                with self.processors_lock:
                    if processor.processor_id in self.processors:
                        self.processors[processor.processor_id].current_load += 1
                        
                logger.info(f"Task {task.id} assigned to {processor.processor_id}")
                return True
            else:
                # Reset assignment if failed
                with self.tasks_lock:
                    task.assigned_processor = None
                    task.status = 'pending'
                return False
                
        except Exception as e:
            logger.error(f"Error assigning task {task.id} to processor {processor.processor_id}: {e}")
            return False
            
    def _assign_to_distributed_network(self, task: ProcessingTask, processor: ProcessorInfo) -> bool:
        """Assign task to distributed network"""
        try:
            # Submit task to distributed network
            network_task_id = self.distributed_network.submit_task(
                task.type, task.data, task.priority, task.deadline
            )
            
            # Store mapping between our task ID and network task ID
            # In a real implementation, we would track this mapping
            logger.info(f"Task {task.id} submitted to distributed network as {network_task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting task {task.id} to distributed network: {e}")
            return False
            
    def _assign_to_local_ai(self, task: ProcessingTask, processor: ProcessorInfo) -> bool:
        """Assign task to local AI coordinator"""
        try:
            # Submit task to local AI coordinator
            local_task_id = self.local_ai_coordinator.submit_task(
                task.type, task.data, task.priority, task.deadline
            )
            
            # Store mapping between our task ID and local task ID
            # In a real implementation, we would track this mapping
            logger.info(f"Task {task.id} submitted to local AI as {local_task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting task {task.id} to local AI: {e}")
            return False
            
    def _monitoring_loop(self):
        """Monitor task progress and processor status"""
        while self.is_running:
            try:
                # Check task progress
                self._check_task_progress()
                
                # Update processor status
                self._update_processor_status()
                
                # Handle completed tasks
                self._handle_completed_tasks()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
                
    def _check_task_progress(self):
        """Check progress of assigned tasks"""
        with self.tasks_lock:
            current_time = time.time()
            for task_id, task in self.tasks.items():
                if task.status == 'assigned' or task.status == 'processing':
                    # Check if task has timed out
                    if task.deadline and current_time > task.deadline:
                        self._handle_task_timeout(task)
                    # Check if task has exceeded retry limit
                    elif task.retry_count >= self.max_retries:
                        self._handle_task_failure(task)
                        
    def _update_processor_status(self):
        """Update status of processors"""
        with self.processors_lock:
            current_time = time.time()
            
            # Update local AI status
            if 'local_ai' in self.processors and self.local_ai_coordinator:
                local_stats = self.local_ai_coordinator.get_coordinator_stats()
                self.processors['local_ai'].status = 'available' if local_stats else 'offline'
                self.processors['local_ai'].last_updated = current_time
                self.processors['local_ai'].current_load = local_stats.get('active_tasks', 0) if local_stats else 0
                
            # Update distributed node status (if we have access to network stats)
            if self.distributed_network:
                network_stats = self.distributed_network.get_network_stats()
                # In a real implementation, we would update individual node statuses
                
    def _handle_completed_tasks(self):
        """Handle completed tasks from processors"""
        # Check distributed network for completed tasks
        if self.distributed_network:
            self._check_distributed_results()
            
        # Check local AI for completed tasks
        if self.local_ai_coordinator:
            self._check_local_results()
            
    def _check_distributed_results(self):
        """Check for completed tasks from distributed network"""
        # In a real implementation, we would check the distributed network for results
        # This is a placeholder for the actual implementation
        pass
        
    def _check_local_results(self):
        """Check for completed tasks from local AI"""
        # In a real implementation, we would check the local AI coordinator for results
        # This is a placeholder for the actual implementation
        pass
        
    def _handle_task_timeout(self, task: ProcessingTask):
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
            
    def _handle_task_failure(self, task: ProcessingTask):
        """Handle task failure"""
        logger.error(f"Task {task.id} failed after {self.max_retries} retries")
        
        with self.tasks_lock:
            task.status = 'failed'
            if not task.result:
                task.result = {'error': 'Task failed after maximum retries'}
                
        with self.stats_lock:
            self.stats['failed_tasks'] += 1
            
    def _retry_task(self, task: ProcessingTask):
        """Retry a failed task"""
        with self.tasks_lock:
            task.retry_count += 1
            task.status = 'pending'
            task.assigned_processor = None
            self.task_queue.append(task)
            
        logger.info(f"Task {task.id} retried (attempt {task.retry_count})")
        
    def get_task_result(self, task_id: str) -> Optional[ProcessingTask]:
        """Get result for a task"""
        with self.tasks_lock:
            return self.tasks.get(task_id)
            
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        with self.stats_lock:
            total = self.stats['total_tasks']
            success_rate = (
                self.stats['completed_tasks'] / total * 100
                if total > 0 else 0
            )
            
            with self.processors_lock:
                available_processors = len([p for p in self.processors.values() if p.status == 'available'])
                
            return {
                **self.stats,
                'success_rate': round(success_rate, 2),
                'available_processors': available_processors,
                'queue_size': len(self.task_queue)
            }
            
    def get_processor_info(self, processor_id: str) -> Optional[ProcessorInfo]:
        """Get information about a specific processor"""
        with self.processors_lock:
            return self.processors.get(processor_id)
            
    def get_all_processors(self) -> Dict[str, ProcessorInfo]:
        """Get information about all processors"""
        with self.processors_lock:
            return self.processors.copy()
            
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self.tasks_lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == 'pending':
                    # Remove from queue if present
                    if task in self.task_queue:
                        self.task_queue.remove(task)
                    # Update status
                    task.status = 'cancelled'
                    return True
        return False
        
    def set_distributed_network(self, network):
        """Set distributed network"""
        self.distributed_network = network
        
    def set_local_ai_coordinator(self, coordinator):
        """Set local AI coordinator"""
        self.local_ai_coordinator = coordinator

# Example usage
if __name__ == "__main__":
    # Initialize hybrid processing engine
    engine = HybridProcessingEngine()
    
    # Start engine
    engine.start_engine()
    
    # Submit sample tasks
    task_data1 = {
        "content": "This is sample content for distributed processing",
        "context": "Sample context"
    }
    
    task_data2 = {
        "content": "This is sample content for local processing",
        "context": "Sample context"
    }
    
    task_id1 = engine.submit_task("verification", task_data1, "high", processing_mode="distributed")
    task_id2 = engine.submit_task("analysis", task_data2, "medium", processing_mode="local")
    
    print(f"Submitted tasks: {task_id1}, {task_id2}")
    
    # Wait for tasks to be processed
    time.sleep(3)
    
    # Check task results
    result1 = engine.get_task_result(task_id1)
    result2 = engine.get_task_result(task_id2)
    
    if result1:
        print(f"Task 1 status: {result1.status}")
    if result2:
        print(f"Task 2 status: {result2.status}")
        
    # Get engine stats
    stats = engine.get_engine_stats()
    print(f"Engine stats: {stats}")
    
    # Stop engine
    engine.stop_engine()