import hashlib
import json
import time
import threading
import ipaddress
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from collections import defaultdict, deque
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    event_type: str  # 'ddos', 'anomaly', 'compromise', 'rate_limit'
    source: str  # IP address or node ID
    timestamp: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    details: Dict[str, Any]
    handled: bool = False

@dataclass
class NodeSecurityStatus:
    node_id: str
    status: str  # 'trusted', 'suspicious', 'compromised', 'blacklisted'
    threat_score: float  # 0.0 to 1.0
    last_updated: float
    incidents: List[str]  # List of incident IDs

@dataclass
class RateLimitRule:
    identifier: str  # IP, node_id, or other identifier
    limit: int  # Number of requests allowed
    window: int  # Time window in seconds
    current_count: int = 0
    window_start: float = 0.0

class AttackResilienceManager:
    def __init__(self, ddos_threshold: int = 1000, anomaly_threshold: float = 2.0):
        """Initialize attack resilience manager"""
        self.ddos_threshold = ddos_threshold
        self.anomaly_threshold = anomaly_threshold
        self.security_events = deque(maxlen=10000)  # Keep last 10k events
        self.node_security_status = {}  # node_id -> NodeSecurityStatus
        self.rate_limit_rules = {}  # identifier -> RateLimitRule
        self.blacklisted_ips = set()  # Set of blacklisted IP addresses
        self.whitelisted_ips = set()  # Set of trusted IP addresses
        self.is_running = False
        self.monitoring_thread = None
        self.incident_response_thread = None
        self.traffic_history = defaultdict(deque)  # source -> deque of timestamps
        self.request_counters = defaultdict(int)  # endpoint -> count
        self.isolation_zones = {}  # zone_id -> list of isolated nodes
        
        # Performance metrics
        self.stats = {
            'total_events': 0,
            'handled_events': 0,
            'blocked_requests': 0,
            'isolated_nodes': 0
        }
        
        # Locks for thread safety
        self.events_lock = threading.Lock()
        self.nodes_lock = threading.Lock()
        self.rate_limit_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
    def start_monitoring(self):
        """Start security monitoring"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Start incident response thread
        self.incident_response_thread = threading.Thread(target=self._incident_response_loop, daemon=True)
        self.incident_response_thread.start()
        
        logger.info("Attack resilience monitoring started")
        
    def stop_monitoring(self):
        """Stop security monitoring"""
        self.is_running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
            
        if self.incident_response_thread:
            self.incident_response_thread.join(timeout=5)
            
        logger.info("Attack resilience monitoring stopped")
        
    def log_request(self, source: str, endpoint: str = "/", user_agent: str = ""):
        """Log incoming request for security monitoring"""
        current_time = time.time()
        
        # Check if source is blacklisted
        if source in self.blacklisted_ips:
            with self.stats_lock:
                self.stats['blocked_requests'] += 1
            return False  # Block request
            
        # Update traffic history
        self.traffic_history[source].append(current_time)
        
        # Keep only recent traffic (last 5 minutes)
        while (self.traffic_history[source] and 
               current_time - self.traffic_history[source][0] > 300):
            self.traffic_history[source].popleft()
            
        # Update request counters
        self.request_counters[endpoint] += 1
        
        # Check for DDoS attack
        if len(self.traffic_history[source]) > self.ddos_threshold:
            self._log_security_event('ddos', source, 'high', {
                'request_count': len(self.traffic_history[source]),
                'time_window': 300
            })
            self._blacklist_source(source)
            
        # Check rate limits
        if not self._check_rate_limit(source):
            return False  # Rate limit exceeded
            
        return True  # Request allowed
        
    def _check_rate_limit(self, identifier: str) -> bool:
        """Check if identifier has exceeded rate limit"""
        current_time = time.time()
        
        with self.rate_limit_lock:
            if identifier not in self.rate_limit_rules:
                # Create new rate limit rule
                self.rate_limit_rules[identifier] = RateLimitRule(
                    identifier=identifier,
                    limit=100,  # Default 100 requests per minute
                    window=60
                )
                
            rule = self.rate_limit_rules[identifier]
            
            # Reset window if needed
            if current_time - rule.window_start > rule.window:
                rule.window_start = current_time
                rule.current_count = 0
                
            # Increment counter
            rule.current_count += 1
            
            # Check if limit exceeded
            if rule.current_count > rule.limit:
                self._log_security_event('rate_limit', identifier, 'medium', {
                    'count': rule.current_count,
                    'limit': rule.limit,
                    'window': rule.window
                })
                return False  # Rate limit exceeded
                
        return True  # Within rate limit
        
    def check_node_security(self, node_id: str, metrics: Dict[str, Any]) -> bool:
        """Check if node behavior is suspicious"""
        threat_score = self._calculate_threat_score(node_id, metrics)
        
        with self.nodes_lock:
            # Update node security status
            if node_id not in self.node_security_status:
                self.node_security_status[node_id] = NodeSecurityStatus(
                    node_id=node_id,
                    status='trusted',
                    threat_score=threat_score,
                    last_updated=time.time(),
                    incidents=[]
                )
            else:
                self.node_security_status[node_id].threat_score = threat_score
                self.node_security_status[node_id].last_updated = time.time()
                
            # Check if node should be isolated
            if threat_score > 0.8:
                self.node_security_status[node_id].status = 'compromised'
                self._isolate_node(node_id)
                return False  # Node is compromised
            elif threat_score > 0.5:
                self.node_security_status[node_id].status = 'suspicious'
                return True  # Node is suspicious but allowed
            else:
                self.node_security_status[node_id].status = 'trusted'
                return True  # Node is trusted
                
    def _calculate_threat_score(self, node_id: str, metrics: Dict[str, Any]) -> float:
        """Calculate threat score for a node based on metrics"""
        score = 0.0
        
        # Check for anomalous CPU usage
        cpu_usage = metrics.get('cpu_usage', 0)
        if cpu_usage > 90:
            score += 0.3
            
        # Check for anomalous memory usage
        memory_usage = metrics.get('memory_usage', 0)
        if memory_usage > 90:
            score += 0.2
            
        # Check for unusual network activity
        network_usage = metrics.get('network_usage', 0)
        if network_usage > 80:
            score += 0.2
            
        # Check for failed task rate
        task_completion_rate = metrics.get('task_completion_rate', 1.0)
        if task_completion_rate < 0.5:
            score += 0.3
            
        # Check node security history
        with self.nodes_lock:
            if node_id in self.node_security_status:
                status = self.node_security_status[node_id]
                if status.status == 'suspicious':
                    score += 0.2
                elif status.status == 'compromised':
                    score += 0.5
                    
        return min(1.0, score)  # Cap at 1.0
        
    def _log_security_event(self, event_type: str, source: str, severity: str, details: Dict[str, Any]):
        """Log a security event"""
        event = SecurityEvent(
            event_type=event_type,
            source=source,
            timestamp=time.time(),
            severity=severity,
            details=details
        )
        
        with self.events_lock:
            self.security_events.append(event)
            self.stats['total_events'] += 1
            
        logger.info(f"Security event logged: {event_type} from {source} (severity: {severity})")
        
    def _blacklist_source(self, source: str):
        """Blacklist a source IP address"""
        self.blacklisted_ips.add(source)
        
        self._log_security_event('blacklist', source, 'high', {
            'action': 'added_to_blacklist'
        })
        
        logger.warning(f"Source {source} added to blacklist")
        
    def _isolate_node(self, node_id: str):
        """Isolate a compromised node"""
        # In a real implementation, this would send isolation commands to the network
        # For now, we'll just log the isolation
        
        with self.nodes_lock:
            if node_id in self.node_security_status:
                self.node_security_status[node_id].status = 'compromised'
                
        self._log_security_event('isolation', node_id, 'critical', {
            'action': 'node_isolated'
        })
        
        with self.stats_lock:
            self.stats['isolated_nodes'] += 1
            
        logger.critical(f"Node {node_id} isolated due to security threat")
        
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                current_time = time.time()
                
                # Check for anomalies in traffic patterns
                self._detect_traffic_anomalies(current_time)
                
                # Check for anomalies in node behavior
                self._detect_node_anomalies(current_time)
                
                # Clean up old data
                self._cleanup_old_data(current_time)
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
                
    def _detect_traffic_anomalies(self, current_time: float):
        """Detect anomalies in traffic patterns"""
        # Calculate average requests per second
        total_requests = sum(len(timestamps) for timestamps in self.traffic_history.values())
        avg_requests_per_second = total_requests / 300  # 5 minutes window
        
        # Check each source for anomalous behavior
        for source, timestamps in self.traffic_history.items():
            if len(timestamps) < 10:  # Need at least 10 requests for analysis
                continue
                
            # Calculate requests per second for this source
            source_requests_per_second = len(timestamps) / 300
            
            # Check if source is significantly above average
            if source_requests_per_second > avg_requests_per_second * self.anomaly_threshold:
                self._log_security_event('anomaly', source, 'medium', {
                    'avg_rps': avg_requests_per_second,
                    'source_rps': source_requests_per_second,
                    'threshold': self.anomaly_threshold
                })
                
    def _detect_node_anomalies(self, current_time: float):
        """Detect anomalies in node behavior"""
        # This would be implemented in conjunction with the distributed network
        # For now, we'll just log that anomaly detection is running
        pass
        
    def _cleanup_old_data(self, current_time: float):
        """Clean up old security data"""
        # Clean up old traffic history (older than 10 minutes)
        cutoff_time = current_time - 600
        sources_to_remove = []
        
        for source, timestamps in self.traffic_history.items():
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()
                
            if not timestamps:
                sources_to_remove.append(source)
                
        for source in sources_to_remove:
            del self.traffic_history[source]
            
        # Clean up old rate limit rules (older than 1 hour with no activity)
        with self.rate_limit_lock:
            rules_to_remove = []
            for identifier, rule in self.rate_limit_rules.items():
                if current_time - rule.window_start > 3600 and rule.current_count == 0:
                    rules_to_remove.append(identifier)
                    
            for identifier in rules_to_remove:
                del self.rate_limit_rules[identifier]
                
    def _incident_response_loop(self):
        """Handle security incidents"""
        while self.is_running:
            try:
                # Process unhandled security events
                unhandled_events = self._get_unhandled_events()
                
                for event in unhandled_events:
                    self._handle_security_event(event)
                    
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in incident response loop: {e}")
                time.sleep(5)
                
    def _get_unhandled_events(self) -> List[SecurityEvent]:
        """Get list of unhandled security events"""
        unhandled = []
        with self.events_lock:
            for event in self.security_events:
                if not event.handled:
                    unhandled.append(event)
        return unhandled
        
    def _handle_security_event(self, event: SecurityEvent):
        """Handle a security event"""
        try:
            if event.event_type == 'ddos':
                self._handle_ddos_event(event)
            elif event.event_type == 'anomaly':
                self._handle_anomaly_event(event)
            elif event.event_type == 'compromise':
                self._handle_compromise_event(event)
            elif event.event_type == 'rate_limit':
                self._handle_rate_limit_event(event)
                
            # Mark event as handled
            event.handled = True
            
            with self.stats_lock:
                self.stats['handled_events'] += 1
                
        except Exception as e:
            logger.error(f"Error handling security event: {e}")
            
    def _handle_ddos_event(self, event: SecurityEvent):
        """Handle DDoS security event"""
        logger.critical(f"DDoS attack detected from {event.source}")
        # In a real implementation, this would trigger DDoS mitigation measures
        
    def _handle_anomaly_event(self, event: SecurityEvent):
        """Handle anomaly security event"""
        logger.warning(f"Anomaly detected from {event.source}")
        # In a real implementation, this would trigger deeper investigation
        
    def _handle_compromise_event(self, event: SecurityEvent):
        """Handle compromise security event"""
        logger.critical(f"Node compromise detected: {event.source}")
        # In a real implementation, this would trigger isolation procedures
        
    def _handle_rate_limit_event(self, event: SecurityEvent):
        """Handle rate limit security event"""
        logger.info(f"Rate limit exceeded by {event.source}")
        # In a real implementation, this might trigger temporary blocking
        
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        with self.stats_lock:
            total = self.stats['total_events']
            handled_rate = (
                self.stats['handled_events'] / total * 100
                if total > 0 else 0
            )
            
            return {
                **self.stats,
                'handled_rate': round(handled_rate, 2),
                'blacklisted_count': len(self.blacklisted_ips),
                'active_threats': len([e for e in self.security_events if not e.handled])
            }
            
    def get_node_security_status(self, node_id: str) -> Optional[NodeSecurityStatus]:
        """Get security status for a specific node"""
        with self.nodes_lock:
            return self.node_security_status.get(node_id)
            
    def get_recent_events(self, limit: int = 50) -> List[SecurityEvent]:
        """Get recent security events"""
        with self.events_lock:
            return list(self.security_events)[-limit:]
            
    def add_to_whitelist(self, source: str):
        """Add source to whitelist"""
        self.whitelisted_ips.add(source)
        if source in self.blacklisted_ips:
            self.blacklisted_ips.remove(source)
            
        logger.info(f"Source {source} added to whitelist")
        
    def remove_from_whitelist(self, source: str):
        """Remove source from whitelist"""
        if source in self.whitelisted_ips:
            self.whitelisted_ips.remove(source)
            
        logger.info(f"Source {source} removed from whitelist")
        
    def create_isolation_zone(self, zone_id: str, nodes: List[str]):
        """Create an isolation zone for suspicious nodes"""
        self.isolation_zones[zone_id] = nodes
        
        logger.info(f"Isolation zone {zone_id} created with {len(nodes)} nodes")
        
    def destroy_isolation_zone(self, zone_id: str):
        """Destroy an isolation zone"""
        if zone_id in self.isolation_zones:
            del self.isolation_zones[zone_id]
            
        logger.info(f"Isolation zone {zone_id} destroyed")

# Example usage
if __name__ == "__main__":
    # Initialize attack resilience manager
    arm = AttackResilienceManager()
    
    # Start monitoring
    arm.start_monitoring()
    
    # Simulate some requests
    for i in range(100):
        source_ip = f"192.168.1.{i % 10}"
        allowed = arm.log_request(source_ip, "/api/data")
        if not allowed:
            print(f"Request from {source_ip} blocked")
            
    # Simulate a DDoS attack
    for i in range(2000):
        source_ip = f"10.0.0.{i % 5}"
        allowed = arm.log_request(source_ip, "/api/data")
        if not allowed:
            print(f"DDoS request from {source_ip} blocked")
            
    # Check security stats
    stats = arm.get_security_stats()
    print(f"Security stats: {stats}")
    
    # Get recent events
    events = arm.get_recent_events(10)
    print(f"Recent events: {len(events)}")
    
    # Stop monitoring
    arm.stop_monitoring()