import hashlib
import json
import time
import threading
import asyncio
import websockets
import ssl
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NodeInfo:
    node_id: str
    address: str
    port: int
    status: str  # 'active', 'inactive', 'compromised'
    last_heartbeat: float
    capabilities: List[str]
    performance_metrics: Dict[str, Any]

@dataclass
class Task:
    id: str
    type: str  # 'verification', 'analysis', 'processing'
    data: Dict[str, Any]
    priority: str  # 'high', 'medium', 'low'
    submitted_at: float
    deadline: Optional[float]
    assigned_node: Optional[str] = None

@dataclass
class TaskResult:
    task_id: str
    result: Dict[str, Any]
    processed_by: str
    processed_at: float
    processing_time: float
    verified: bool = False

class DistributedNetwork:
    def __init__(self, local_address: str = "127.0.0.1", local_port: int = 8765):
        """Initialize distributed network"""
        self.local_address = local_address
        self.local_port = local_port
        self.node_id = self._generate_node_id()
        self.nodes = {}  # node_id -> NodeInfo
        self.tasks = {}  # task_id -> Task
        self.task_results = {}  # task_id -> TaskResult
        self.task_queue = []  # List of unassigned tasks
        self.websocket_server = None
        self.websocket_clients = {}  # node_id -> websocket connection
        self.is_running = False
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_thread = None
        self.task_assignment_thread = None
        self.local_ai_available = False
        self.local_ai_coordinator = None
        
        # Performance metrics
        self.network_stats = {
            'total_nodes': 0,
            'active_nodes': 0,
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0
        }
        
        # Locks for thread safety
        self.nodes_lock = threading.Lock()
        self.tasks_lock = threading.Lock()
        self.results_lock = threading.Lock()
        
    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        return hashlib.sha256(f"{self.local_address}:{self.local_port}:{time.time()}".encode()).hexdigest()[:16]
        
    async def start_network(self):
        """Start the distributed network"""
        self.is_running = True
        
        # Start WebSocket server
        self.websocket_server = await websockets.serve(
            self._handle_client_connection,
            self.local_address,
            self.local_port
        )
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        # Start task assignment thread
        self.task_assignment_thread = threading.Thread(target=self._task_assignment_loop, daemon=True)
        self.task_assignment_thread.start()
        
        logger.info(f"Distributed network started on {self.local_address}:{self.local_port}")
        logger.info(f"Node ID: {self.node_id}")
        
    async def stop_network(self):
        """Stop the distributed network"""
        self.is_running = False
        
        # Close WebSocket connections
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
            
        # Close client connections
        for client in self.websocket_clients.values():
            await client.close()
            
        logger.info("Distributed network stopped")
        
    async def _handle_client_connection(self, websocket, path):
        """Handle incoming WebSocket connections"""
        try:
            # Receive node registration message
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get('type') == 'register':
                node_id = data.get('node_id')
                address = data.get('address')
                port = data.get('port')
                capabilities = data.get('capabilities', [])
                
                # Register node
                with self.nodes_lock:
                    self.nodes[node_id] = NodeInfo(
                        node_id=node_id,
                        address=address,
                        port=port,
                        status='active',
                        last_heartbeat=time.time(),
                        capabilities=capabilities,
                        performance_metrics={}
                    )
                    self.websocket_clients[node_id] = websocket
                    self.network_stats['total_nodes'] = len(self.nodes)
                    self.network_stats['active_nodes'] = len([n for n in self.nodes.values() if n.status == 'active'])
                    
                logger.info(f"Node {node_id} registered from {address}:{port}")
                
                # Send acknowledgment
                await websocket.send(json.dumps({
                    'type': 'registration_ack',
                    'status': 'success',
                    'node_id': node_id,
                    'assigned_role': 'worker'
                }))
                
                # Handle node messages
                await self._handle_node_messages(node_id, websocket)
                
        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
            
    async def _handle_node_messages(self, node_id: str, websocket):
        """Handle messages from a connected node"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    if message_type == 'heartbeat':
                        await self._handle_heartbeat(node_id, data)
                    elif message_type == 'task_result':
                        await self._handle_task_result(node_id, data)
                    elif message_type == 'node_status':
                        await self._handle_node_status(node_id, data)
                    else:
                        logger.warning(f"Unknown message type from node {node_id}: {message_type}")
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from node {node_id}")
                except Exception as e:
                    logger.error(f"Error processing message from node {node_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Node {node_id} disconnected")
            await self._handle_node_disconnect(node_id)
        except Exception as e:
            logger.error(f"Error in node message handling for {node_id}: {e}")
            await self._handle_node_disconnect(node_id)
            
    async def _handle_heartbeat(self, node_id: str, data: Dict[str, Any]):
        """Handle heartbeat from node"""
        with self.nodes_lock:
            if node_id in self.nodes:
                self.nodes[node_id].last_heartbeat = time.time()
                self.nodes[node_id].status = 'active'
                self.nodes[node_id].performance_metrics = data.get('metrics', {})
                
        # Send heartbeat acknowledgment
        if node_id in self.websocket_clients:
            try:
                await self.websocket_clients[node_id].send(json.dumps({
                    'type': 'heartbeat_ack',
                    'timestamp': time.time()
                }))
            except Exception as e:
                logger.error(f"Error sending heartbeat ack to {node_id}: {e}")
                
    async def _handle_task_result(self, node_id: str, data: Dict[str, Any]):
        """Handle task result from node"""
        task_id = data.get('task_id')
        result_data = data.get('result', {})
        processing_time = data.get('processing_time', 0)
        
        with self.results_lock:
            # Store task result
            self.task_results[task_id] = TaskResult(
                task_id=task_id,
                result=result_data,
                processed_by=node_id,
                processed_at=time.time(),
                processing_time=processing_time,
                verified=False  # Will be verified separately
            )
            
            # Update network stats
            self.network_stats['completed_tasks'] += 1
            
        logger.info(f"Task {task_id} completed by node {node_id}")
        
        # Remove task from active tasks
        with self.tasks_lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                
    async def _handle_node_status(self, node_id: str, data: Dict[str, Any]):
        """Handle node status update"""
        status = data.get('status')
        metrics = data.get('metrics', {})
        
        with self.nodes_lock:
            if node_id in self.nodes:
                self.nodes[node_id].status = status
                self.nodes[node_id].performance_metrics = metrics
                self.network_stats['active_nodes'] = len([n for n in self.nodes.values() if n.status == 'active'])
                
        logger.info(f"Node {node_id} status updated to {status}")
        
    async def _handle_node_disconnect(self, node_id: str):
        """Handle node disconnection"""
        with self.nodes_lock:
            if node_id in self.nodes:
                self.nodes[node_id].status = 'inactive'
                self.network_stats['active_nodes'] = len([n for n in self.nodes.values() if n.status == 'active'])
                
            if node_id in self.websocket_clients:
                del self.websocket_clients[node_id]
                
        # Reassign tasks from disconnected node
        await self._reassign_node_tasks(node_id)
        
        logger.info(f"Node {node_id} disconnected and tasks reassigned")
        
    async def _reassign_node_tasks(self, node_id: str):
        """Reassign tasks from disconnected node"""
        with self.tasks_lock:
            reassigned_tasks = []
            for task_id, task in self.tasks.items():
                if task.assigned_node == node_id:
                    task.assigned_node = None
                    reassigned_tasks.append(task_id)
                    self.task_queue.append(task)
                    
        if reassigned_tasks:
            logger.info(f"Reassigned {len(reassigned_tasks)} tasks from node {node_id}")
            
    def _heartbeat_loop(self):
        """Send heartbeats to connected nodes"""
        while self.is_running:
            try:
                current_time = time.time()
                inactive_nodes = []
                
                with self.nodes_lock:
                    for node_id, node in self.nodes.items():
                        # Check if node is inactive (no heartbeat for 2 minutes)
                        if current_time - node.last_heartbeat > 120:
                            node.status = 'inactive'
                            inactive_nodes.append(node_id)
                            
                # Handle inactive nodes
                for node_id in inactive_nodes:
                    asyncio.run_coroutine_threadsafe(
                        self._handle_node_disconnect(node_id),
                        asyncio.get_event_loop()
                    )
                    
                # Send heartbeats to active nodes
                active_nodes = [node_id for node_id, node in self.nodes.items() if node.status == 'active']
                for node_id in active_nodes:
                    if node_id in self.websocket_clients:
                        asyncio.run_coroutine_threadsafe(
                            self._send_heartbeat(node_id),
                            asyncio.get_event_loop()
                        )
                        
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(5)
                
    async def _send_heartbeat(self, node_id: str):
        """Send heartbeat to a node"""
        try:
            if node_id in self.websocket_clients:
                metrics = self._get_node_metrics()
                await self.websocket_clients[node_id].send(json.dumps({
                    'type': 'heartbeat',
                    'timestamp': time.time(),
                    'metrics': metrics
                }))
        except Exception as e:
            logger.error(f"Error sending heartbeat to {node_id}: {e}")
            
    def _get_node_metrics(self) -> Dict[str, Any]:
        """Get node performance metrics"""
        # In a real implementation, this would collect actual metrics
        return {
            'cpu_usage': random.uniform(0, 100),
            'memory_usage': random.uniform(0, 100),
            'network_latency': random.uniform(0, 100),
            'task_completion_rate': random.uniform(0, 1)
        }
        
    def _task_assignment_loop(self):
        """Assign tasks to available nodes"""
        while self.is_running:
            try:
                # Get available nodes
                available_nodes = self._get_available_nodes()
                
                if available_nodes and self.task_queue:
                    # Assign tasks to available nodes
                    assigned_count = 0
                    for task in self.task_queue[:]:  # Copy to avoid modification during iteration
                        if available_nodes:
                            # Select node based on capabilities and performance
                            selected_node = self._select_best_node(task, available_nodes)
                            if selected_node:
                                # Assign task to node
                                success = asyncio.run_coroutine_threadsafe(
                                    self._assign_task_to_node(task, selected_node),
                                    asyncio.get_event_loop()
                                ).result()
                                
                                if success:
                                    self.task_queue.remove(task)
                                    assigned_count += 1
                                    available_nodes.remove(selected_node)  # Remove node to avoid overloading
                                    
                    if assigned_count > 0:
                        logger.info(f"Assigned {assigned_count} tasks to nodes")
                        
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in task assignment loop: {e}")
                time.sleep(5)
                
    def _get_available_nodes(self) -> List[str]:
        """Get list of available nodes"""
        with self.nodes_lock:
            return [
                node_id for node_id, node in self.nodes.items()
                if node.status == 'active'
            ]
            
    def _select_best_node(self, task: Task, available_nodes: List[str]) -> Optional[str]:
        """Select the best node for a task based on capabilities and performance"""
        with self.nodes_lock:
            # Filter nodes by capabilities
            capable_nodes = []
            for node_id in available_nodes:
                if node_id in self.nodes:
                    node = self.nodes[node_id]
                    # Check if node has required capabilities
                    if not task.type or task.type in node.capabilities:
                        capable_nodes.append(node_id)
                        
            if not capable_nodes:
                return None
                
            # Select node with best performance metrics
            # For now, we'll randomly select from capable nodes
            # In a real implementation, we would consider performance metrics
            return random.choice(capable_nodes)
            
    async def _assign_task_to_node(self, task: Task, node_id: str) -> bool:
        """Assign task to a specific node"""
        try:
            if node_id in self.websocket_clients:
                # Update task assignment
                with self.tasks_lock:
                    task.assigned_node = node_id
                    self.tasks[task.id] = task
                    
                # Send task to node
                task_message = {
                    'type': 'task_assignment',
                    'task_id': task.id,
                    'task_type': task.type,
                    'data': task.data,
                    'priority': task.priority,
                    'deadline': task.deadline
                }
                
                await self.websocket_clients[node_id].send(json.dumps(task_message))
                logger.info(f"Task {task.id} assigned to node {node_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error assigning task {task.id} to node {node_id}: {e}")
            
        return False
        
    def submit_task(self, task_type: str, data: Dict[str, Any], priority: str = 'medium', 
                   deadline: Optional[float] = None) -> str:
        """Submit a task to the network"""
        # Generate task ID
        task_id = hashlib.sha256(f"{task_type}:{time.time()}:{random.random()}".encode()).hexdigest()[:16]
        
        # Create task
        task = Task(
            id=task_id,
            type=task_type,
            data=data,
            priority=priority,
            submitted_at=time.time(),
            deadline=deadline
        )
        
        # Add to task queue
        with self.tasks_lock:
            self.tasks[task_id] = task
            self.task_queue.append(task)
            self.network_stats['total_tasks'] += 1
            
        logger.info(f"Task {task_id} submitted to network")
        return task_id
        
    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get result for a completed task"""
        with self.results_lock:
            return self.task_results.get(task_id)
            
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        with self.nodes_lock:
            self.network_stats['active_nodes'] = len([n for n in self.nodes.values() if n.status == 'active'])
            
        return self.network_stats.copy()
        
    def get_node_info(self, node_id: str) -> Optional[NodeInfo]:
        """Get information about a specific node"""
        with self.nodes_lock:
            return self.nodes.get(node_id)
            
    def get_all_nodes(self) -> Dict[str, NodeInfo]:
        """Get information about all nodes"""
        with self.nodes_lock:
            return self.nodes.copy()
            
    def set_local_ai_status(self, available: bool):
        """Set local AI availability status"""
        self.local_ai_available = available
        logger.info(f"Local AI availability set to: {available}")
        
    def set_local_ai_coordinator(self, coordinator):
        """Set local AI coordinator"""
        self.local_ai_coordinator = coordinator

# Example usage
if __name__ == "__main__":
    # Initialize distributed network
    network = DistributedNetwork("127.0.0.1", 8765)
    
    # Start network
    async def main():
        await network.start_network()
        
        # Submit a sample task
        task_data = {
            "content": "Sample content for processing",
            "context": "Sample context"
        }
        
        task_id = network.submit_task("analysis", task_data, "medium")
        print(f"Submitted task: {task_id}")
        
        # Wait for a bit
        await asyncio.sleep(10)
        
        # Check task result
        result = network.get_task_result(task_id)
        if result:
            print(f"Task result: {result}")
            
        # Get network stats
        stats = network.get_network_stats()
        print(f"Network stats: {stats}")
        
        # Stop network
        await network.stop_network()
        
    # Run the example
    asyncio.run(main())