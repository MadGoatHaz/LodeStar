import hashlib
import json
import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VerificationRequest:
    id: str
    data: Dict[str, Any]
    signature: str
    crawler_id: str
    public_key: str
    submitted_at: float
    status: str  # 'pending', 'verified', 'rejected', 'conflict'
    verification_result: Optional[Dict[str, Any]] = None
    verified_by: Optional[List[str]] = None  # List of verifier IDs

@dataclass
class Verifier:
    id: str
    reputation_score: float  # 0.0 to 10.0
    capabilities: List[str]  # List of data types this verifier can handle
    last_active: float
    performance_metrics: Dict[str, Any]

@dataclass
class ConsensusResult:
    request_id: str
    data_hash: str
    verifications: int
    required_verifications: int
    consensus_reached: bool
    final_status: str  # 'verified', 'rejected', 'conflict'
    confidence_level: float
    verified_data: Optional[Dict[str, Any]] = None

class CrawlerVerificationPipeline:
    def __init__(self, required_verifications: int = 3, threshold: float = 0.8):
        """Initialize crawler verification pipeline"""
        self.required_verifications = required_verifications
        self.threshold = threshold
        self.verification_requests = {}  # request_id -> VerificationRequest
        self.verifiers = {}  # verifier_id -> Verifier
        self.consensus_results = {}  # request_id -> ConsensusResult
        self.trusted_keys = set()  # Set of trusted public key PEMs
        self.is_running = False
        self.verification_thread = None
        self.consensus_thread = None
        
        # Performance metrics
        self.stats = {
            'total_requests': 0,
            'verified_requests': 0,
            'rejected_requests': 0,
            'conflicts_resolved': 0
        }
        
        # Locks for thread safety
        self.requests_lock = threading.Lock()
        self.verifiers_lock = threading.Lock()
        self.consensus_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
    def start_pipeline(self):
        """Start the verification pipeline"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start verification thread
        self.verification_thread = threading.Thread(target=self._verification_loop, daemon=True)
        self.verification_thread.start()
        
        # Start consensus thread
        self.consensus_thread = threading.Thread(target=self._consensus_loop, daemon=True)
        self.consensus_thread.start()
        
        logger.info("Crawler verification pipeline started")
        
    def stop_pipeline(self):
        """Stop the verification pipeline"""
        self.is_running = False
        
        if self.verification_thread:
            self.verification_thread.join(timeout=5)
            
        if self.consensus_thread:
            self.consensus_thread.join(timeout=5)
            
        logger.info("Crawler verification pipeline stopped")
        
    def add_trusted_key(self, public_key_pem: str):
        """Add a trusted public key"""
        self.trusted_keys.add(public_key_pem)
        logger.info("Trusted key added")
        
    def remove_trusted_key(self, public_key_pem: str):
        """Remove a trusted public key"""
        if public_key_pem in self.trusted_keys:
            self.trusted_keys.remove(public_key_pem)
            logger.info("Trusted key removed")
            
    def is_trusted_key(self, public_key_pem: str) -> bool:
        """Check if a public key is trusted"""
        return public_key_pem in self.trusted_keys
        
    def submit_for_verification(self, data: Dict[str, Any], signature: str, 
                               crawler_id: str, public_key_pem: str) -> str:
        """Submit data for verification"""
        # Generate request ID
        request_id = hashlib.sha256(f"{crawler_id}:{time.time()}:{hash(str(data))}".encode()).hexdigest()[:16]
        
        # Create verification request
        request = VerificationRequest(
            id=request_id,
            data=data,
            signature=signature,
            crawler_id=crawler_id,
            public_key=public_key_pem,
            submitted_at=time.time(),
            status='pending',
            verified_by=[]
        )
        
        # Add to verification queue
        with self.requests_lock:
            self.verification_requests[request_id] = request
            self.stats['total_requests'] += 1
            
        logger.info(f"Verification request {request_id} submitted for crawler {crawler_id}")
        return request_id
        
    def register_verifier(self, verifier_id: str, capabilities: List[str], reputation_score: float = 5.0):
        """Register a verifier"""
        verifier = Verifier(
            id=verifier_id,
            reputation_score=reputation_score,
            capabilities=capabilities,
            last_active=time.time(),
            performance_metrics={}
        )
        
        with self.verifiers_lock:
            self.verifiers[verifier_id] = verifier
            
        logger.info(f"Verifier {verifier_id} registered with capabilities: {capabilities}")
        
    def _verification_loop(self):
        """Main verification loop"""
        while self.is_running:
            try:
                # Get pending requests
                pending_requests = self._get_pending_requests()
                
                # Assign requests to verifiers
                for request in pending_requests:
                    self._assign_request_to_verifiers(request)
                    
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in verification loop: {e}")
                time.sleep(5)
                
    def _get_pending_requests(self) -> List[VerificationRequest]:
        """Get list of pending verification requests"""
        with self.requests_lock:
            return [
                request for request in self.verification_requests.values()
                if request.status == 'pending'
            ]
            
    def _assign_request_to_verifiers(self, request: VerificationRequest):
        """Assign verification request to available verifiers"""
        available_verifiers = self._get_available_verifiers()
        
        if not available_verifiers:
            return
            
        # Filter verifiers by capabilities
        capable_verifiers = [
            v for v in available_verifiers 
            if self._is_verifier_capable(v, request)
        ]
        
        if not capable_verifiers:
            return
            
        # Select verifiers based on reputation and availability
        selected_verifiers = self._select_verifiers(capable_verifiers, self.required_verifications)
        
        # Assign request to selected verifiers
        for verifier in selected_verifiers:
            self._assign_request_to_verifier(request, verifier)
            
    def _get_available_verifiers(self) -> List[Verifier]:
        """Get list of available verifiers"""
        with self.verifiers_lock:
            current_time = time.time()
            return [
                verifier for verifier in self.verifiers.values()
                if (current_time - verifier.last_active) < 300  # Active within last 5 minutes
            ]
            
    def _is_verifier_capable(self, verifier: Verifier, request: VerificationRequest) -> bool:
        """Check if verifier is capable of verifying this request"""
        # Check if verifier has capabilities for this data type
        data_type = request.data.get('source_type', 'generic')
        return data_type in verifier.capabilities or 'generic' in verifier.capabilities
        
    def _select_verifiers(self, verifiers: List[Verifier], count: int) -> List[Verifier]:
        """Select verifiers based on reputation and diversity"""
        if len(verifiers) <= count:
            return verifiers
            
        # Weight verifiers by reputation score
        weighted_verifiers = []
        for verifier in verifiers:
            weight = verifier.reputation_score
            weighted_verifiers.append((verifier, weight))
            
        # Sort by weight (higher reputation first)
        weighted_verifiers.sort(key=lambda x: x[1], reverse=True)
        
        # Select top verifiers
        selected = [v[0] for v in weighted_verifiers[:count]]
        return selected
        
    def _assign_request_to_verifier(self, request: VerificationRequest, verifier: Verifier):
        """Assign request to a specific verifier"""
        try:
            # In a real implementation, we would send the request to the verifier
            # For now, we'll simulate the verification process
            logger.info(f"Assigning request {request.id} to verifier {verifier.id}")
            
            # Update verifier last active time
            with self.verifiers_lock:
                if verifier.id in self.verifiers:
                    self.verifiers[verifier.id].last_active = time.time()
                    
            # Start verification in a separate thread
            verify_thread = threading.Thread(
                target=self._execute_verification, 
                args=(request, verifier), 
                daemon=True
            )
            verify_thread.start()
            
        except Exception as e:
            logger.error(f"Error assigning request {request.id} to verifier {verifier.id}: {e}")
            
    def _execute_verification(self, request: VerificationRequest, verifier: Verifier):
        """Execute verification (simulated)"""
        try:
            logger.info(f"Verifying request {request.id} with verifier {verifier.id}")
            
            # Verify signature
            is_valid = self._verify_signature(request.data, request.signature, request.public_key)
            
            # Verify crawler is trusted
            is_trusted = self.is_trusted_key(request.public_key)
            
            # Create verification result
            verification_result = {
                "is_valid_signature": is_valid,
                "is_trusted_crawler": is_trusted,
                "verified_at": time.time(),
                "verifier_id": verifier.id,
                "confidence": min(1.0, (is_valid + is_trusted) / 2.0)  # Simple confidence calculation
            }
            
            # Update request
            with self.requests_lock:
                if request.id in self.verification_requests:
                    self.verification_requests[request.id].verification_result = verification_result
                    self.verification_requests[request.id].verified_by.append(verifier.id)
                    
                    # Update verifier performance metrics
                    with self.verifiers_lock:
                        if verifier.id in self.verifiers:
                            verifier_stats = self.verifiers[verifier.id].performance_metrics
                            verifier_stats['total_verifications'] = verifier_stats.get('total_verifications', 0) + 1
                            if is_valid and is_trusted:
                                verifier_stats['successful_verifications'] = verifier_stats.get('successful_verifications', 0) + 1
                                
            logger.info(f"Verification completed for request {request.id} by verifier {verifier.id}")
            
        except Exception as e:
            logger.error(f"Error verifying request {request.id} with verifier {verifier.id}: {e}")
            
    def _verify_signature(self, data: Dict[str, Any], signature: str, public_key_pem: str) -> bool:
        """Verify data signature"""
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )
            
            # Convert data to JSON string and encode
            data_json = json.dumps(data, sort_keys=True)
            data_bytes = data_json.encode('utf-8')
            
            # Decode signature from base64
            signature_bytes = base64.b64decode(signature.encode('utf-8'))
            
            # Verify signature
            public_key.verify(
                signature_bytes,
                data_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
            
    def _consensus_loop(self):
        """Main consensus loop"""
        while self.is_running:
            try:
                # Check for requests ready for consensus
                ready_requests = self._get_ready_for_consensus()
                
                # Process consensus for each request
                for request in ready_requests:
                    self._process_consensus(request)
                    
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in consensus loop: {e}")
                time.sleep(5)
                
    def _get_ready_for_consensus(self) -> List[VerificationRequest]:
        """Get list of requests ready for consensus"""
        with self.requests_lock:
            return [
                request for request in self.verification_requests.values()
                if (request.status == 'pending' and 
                    len(request.verified_by or []) >= self.required_verifications)
            ]
            
    def _process_consensus(self, request: VerificationRequest):
        """Process consensus for a request"""
        try:
            # Calculate consensus
            consensus_result = self._calculate_consensus(request)
            
            # Store consensus result
            with self.consensus_lock:
                self.consensus_results[request.id] = consensus_result
                
            # Update request status
            with self.requests_lock:
                if request.id in self.verification_requests:
                    self.verification_requests[request.id].status = consensus_result.final_status
                    
            # Update statistics
            with self.stats_lock:
                if consensus_result.final_status == 'verified':
                    self.stats['verified_requests'] += 1
                elif consensus_result.final_status == 'rejected':
                    self.stats['rejected_requests'] += 1
                    
            logger.info(f"Consensus reached for request {request.id}: {consensus_result.final_status}")
            
        except Exception as e:
            logger.error(f"Error processing consensus for request {request.id}: {e}")
            
    def _calculate_consensus(self, request: VerificationRequest) -> ConsensusResult:
        """Calculate consensus for a request"""
        # Calculate data hash
        data_hash = hashlib.sha256(
            json.dumps(request.data, sort_keys=True).encode()
        ).hexdigest()
        
        # Count verified vs rejected
        verified_count = 0
        rejected_count = 0
        total_verifications = len(request.verified_by or [])
        
        # In a real implementation, we would analyze verification results
        # For now, we'll simulate based on signature validity and trusted status
        if request.verification_result:
            is_valid = request.verification_result.get('is_valid_signature', False)
            is_trusted = request.verification_result.get('is_trusted_crawler', False)
            
            if is_valid and is_trusted:
                verified_count = total_verifications
            else:
                rejected_count = total_verifications
                
        # Calculate confidence level
        confidence_level = max(verified_count, rejected_count) / total_verifications if total_verifications > 0 else 0
        
        # Determine final status
        if verified_count >= self.required_verifications:
            final_status = 'verified'
        elif rejected_count >= self.required_verifications:
            final_status = 'rejected'
        else:
            final_status = 'conflict'
            
        return ConsensusResult(
            request_id=request.id,
            data_hash=data_hash,
            verifications=total_verifications,
            required_verifications=self.required_verifications,
            consensus_reached=(final_status in ['verified', 'rejected']),
            final_status=final_status,
            confidence_level=confidence_level,
            verified_data=request.data if final_status == 'verified' else None
        )
        
    def get_verification_result(self, request_id: str) -> Optional[ConsensusResult]:
        """Get verification result for a request"""
        with self.consensus_lock:
            return self.consensus_results.get(request_id)
            
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        with self.stats_lock:
            total = self.stats['total_requests']
            success_rate = (
                (self.stats['verified_requests'] + self.stats['rejected_requests']) / total * 100
                if total > 0 else 0
            )
            
            return {
                **self.stats,
                'success_rate': round(success_rate, 2),
                'pending_requests': len(self._get_pending_requests()),
                'active_verifiers': len(self._get_available_verifiers())
            }
            
    def get_verifier_info(self, verifier_id: str) -> Optional[Verifier]:
        """Get information about a specific verifier"""
        with self.verifiers_lock:
            return self.verifiers.get(verifier_id)
            
    def get_all_verifiers(self) -> Dict[str, Verifier]:
        """Get information about all verifiers"""
        with self.verifiers_lock:
            return self.verifiers.copy()
            
    def update_verifier_reputation(self, verifier_id: str, score_change: float):
        """Update verifier reputation score"""
        with self.verifiers_lock:
            if verifier_id in self.verifiers:
                current_score = self.verifiers[verifier_id].reputation_score
                new_score = max(0.0, min(10.0, current_score + score_change))
                self.verifiers[verifier_id].reputation_score = new_score
                logger.info(f"Verifier {verifier_id} reputation updated to {new_score}")

# Example usage
if __name__ == "__main__":
    # Initialize verification pipeline
    pipeline = CrawlerVerificationPipeline()
    
    # Start pipeline
    pipeline.start_pipeline()
    
    # Add trusted key (in a real system, this would be loaded from a file)
    trusted_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxq5zXvJjR7eVQYhW5JkM
... (example key) ...
-----END PUBLIC KEY-----"""
    pipeline.add_trusted_key(trusted_key)
    
    # Register sample verifiers
    pipeline.register_verifier("verifier_1", ["youtube", "twitter"], 8.0)
    pipeline.register_verifier("verifier_2", ["brave_search", "generic"], 7.5)
    pipeline.register_verifier("verifier_3", ["youtube", "generic"], 9.0)
    
    # Submit sample verification request
    sample_data = {
        "url": "https://youtube.com/sample_video",
        "source_type": "youtube",
        "content": "Sample content",
        "timestamp": time.time()
    }
    
    # In a real implementation, this would be a real signature
    sample_signature = "sample_signature_base64"
    
    request_id = pipeline.submit_for_verification(
        sample_data, 
        sample_signature, 
        "crawler_1", 
        trusted_key
    )
    
    print(f"Submitted verification request: {request_id}")
    
    # Wait for verification to complete
    time.sleep(15)
    
    # Check verification result
    result = pipeline.get_verification_result(request_id)
    if result:
        print(f"Verification result: {result.final_status}")
        
    # Get pipeline stats
    stats = pipeline.get_pipeline_stats()
    print(f"Pipeline stats: {stats}")
    
    # Stop pipeline
    pipeline.stop_pipeline()