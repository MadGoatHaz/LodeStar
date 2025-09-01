import hashlib
import json
import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import random

@dataclass
class Submission:
    id: str
    data: Dict[str, Any]
    signature: str
    volunteer_id: str
    submission_time: float
    data_hash: str
    public_key: str

@dataclass
class Verification:
    submission_id: str
    verifier_id: str
    verification_time: float
    signature: str
    status: str  # 'verified', 'rejected', 'pending'
    confidence_score: float

@dataclass
class ConsensusResult:
    submission_id: str
    data_hash: str
    verifications: int
    required_verifications: int
    consensus_reached: bool
    final_status: str  # 'verified', 'rejected'
    confidence_level: float
    ipfs_hash: Optional[str] = None

class VerificationNetwork:
    def __init__(self, min_verifications: int = 3):
        """Initialize verification network"""
        self.min_verifications = min_verifications
        self.submissions = {}  # submission_id -> Submission
        self.verifications = defaultdict(list)  # submission_id -> List[Verification]
        self.verifiers = {}  # verifier_id -> verifier_info
        self.consensus_results = {}  # submission_id -> ConsensusResult
        self.reputation_scores = defaultdict(float)  # verifier_id -> reputation_score
        self.network_stats = {
            'total_submissions': 0,
            'verified_submissions': 0,
            'rejected_submissions': 0,
            'pending_submissions': 0
        }
        self.lock = threading.Lock()
        
    def register_verifier(self, verifier_id: str, verifier_info: Dict[str, Any]):
        """Register a new verifier"""
        with self.lock:
            self.verifiers[verifier_id] = verifier_info
            if verifier_id not in self.reputation_scores:
                self.reputation_scores[verifier_id] = 1.0  # Default reputation score
            print(f"Verifier {verifier_id} registered")
            
    def submit_for_verification(self, submission: Submission) -> bool:
        """Submit data for verification"""
        with self.lock:
            # Validate submission
            if not self._validate_submission(submission):
                print(f"Invalid submission: {submission.id}")
                return False
                
            # Store submission
            self.submissions[submission.id] = submission
            self.network_stats['total_submissions'] += 1
            self.network_stats['pending_submissions'] += 1
            
            # Assign to verifiers
            self._assign_verification(submission.id)
            
            print(f"Submission {submission.id} submitted for verification")
            return True
            
    def _validate_submission(self, submission: Submission) -> bool:
        """Validate submission integrity"""
        # Check if submission ID is unique
        if submission.id in self.submissions:
            return False
            
        # Verify data hash
        calculated_hash = hashlib.sha256(
            json.dumps(submission.data, sort_keys=True).encode()
        ).hexdigest()
        
        if calculated_hash != submission.data_hash:
            return False
            
        # In a real implementation, we would also verify the signature
        # using the provided public key
        
        return True
        
    def _assign_verification(self, submission_id: str):
        """Assign submission to multiple verifiers"""
        # Get available verifiers (excluding the submitter)
        available_verifiers = [
            vid for vid in self.verifiers.keys() 
            if vid != self.submissions[submission_id].volunteer_id
        ]
        
        # Select diverse verifiers
        selected_verifiers = self._select_diverse_verifiers(
            available_verifiers, 
            self.min_verifications
        )
        
        # Create verification requests
        for verifier_id in selected_verifiers:
            verification = Verification(
                submission_id=submission_id,
                verifier_id=verifier_id,
                verification_time=time.time(),
                signature="",  # Will be filled when verification is complete
                status="pending",
                confidence_score=0.0
            )
            self.verifications[submission_id].append(verification)
            
        print(f"Assigned {len(selected_verifiers)} verifiers to submission {submission_id}")
        
    def _select_diverse_verifiers(self, verifiers: List[str], count: int) -> List[str]:
        """Select diverse verifiers to minimize collusion risk"""
        if len(verifiers) <= count:
            return verifiers
            
        # Weight verifiers by reputation score
        weights = [self.reputation_scores.get(vid, 1.0) for vid in verifiers]
        
        # Select verifiers with weighted random selection
        selected = []
        available_verifiers = verifiers.copy()
        available_weights = weights.copy()
        
        for _ in range(min(count, len(verifiers))):
            if not available_verifiers:
                break
                
            # Select verifier based on weights
            chosen_index = self._weighted_choice(available_weights)
            selected.append(available_verifiers[chosen_index])
            
            # Remove selected verifier
            del available_verifiers[chosen_index]
            del available_weights[chosen_index]
            
        return selected
        
    def _weighted_choice(self, weights: List[float]) -> int:
        """Select index based on weights"""
        total = sum(weights)
        if total <= 0:
            return random.randint(0, len(weights) - 1)
            
        r = random.uniform(0, total)
        upto = 0
        for i, w in enumerate(weights):
            upto += w
            if upto >= r:
                return i
        return len(weights) - 1
        
    def submit_verification(self, verification: Verification) -> bool:
        """Submit verification result"""
        with self.lock:
            # Validate verification
            if not self._validate_verification(verification):
                print(f"Invalid verification for submission {verification.submission_id}")
                return False
                
            # Store verification
            self.verifications[verification.submission_id].append(verification)
            
            # Update verifier reputation
            self._update_reputation(verification)
            
            # Check for consensus
            consensus_result = self._check_consensus(verification.submission_id)
            if consensus_result:
                self.consensus_results[verification.submission_id] = consensus_result
                self._update_network_stats(consensus_result)
                
                # Remove from pending count
                self.network_stats['pending_submissions'] = max(
                    0, self.network_stats['pending_submissions'] - 1
                )
                
                print(f"Consensus reached for submission {verification.submission_id}: {consensus_result.final_status}")
                
            return True
            
    def _validate_verification(self, verification: Verification) -> bool:
        """Validate verification integrity"""
        # Check if submission exists
        if verification.submission_id not in self.submissions:
            return False
            
        # Check if verifier is registered
        if verification.verifier_id not in self.verifiers:
            return False
            
        # Check if verifier has already verified this submission
        existing_verifications = [
            v for v in self.verifications[verification.submission_id]
            if v.verifier_id == verification.verifier_id
        ]
        
        if existing_verifications:
            return False
            
        # In a real implementation, we would also verify the signature
        # using the verifier's public key
        
        return True
        
    def _update_reputation(self, verification: Verification):
        """Update verifier reputation based on verification quality"""
        verifier_id = verification.verifier_id
        
        # Simple reputation update - increase for correct verifications
        if verification.status in ['verified', 'rejected']:
            self.reputation_scores[verifier_id] += 0.1
        else:
            self.reputation_scores[verifier_id] -= 0.05
            
        # Keep reputation between 0 and 10
        self.reputation_scores[verifier_id] = max(0, min(10, self.reputation_scores[verifier_id]))
        
    def _check_consensus(self, submission_id: str) -> Optional[ConsensusResult]:
        """Check if consensus has been reached for a submission"""
        verifications = self.verifications[submission_id]
        
        # Need minimum verifications
        if len(verifications) < self.min_verifications:
            return None
            
        # Count verified vs rejected
        verified_count = sum(1 for v in verifications if v.status == 'verified')
        rejected_count = sum(1 for v in verifications if v.status == 'rejected')
        total_verifications = len(verifications)
        
        # Calculate confidence level
        confidence_level = max(verified_count, rejected_count) / total_verifications
        
        # Check if consensus is reached
        if verified_count >= self.min_verifications:
            return ConsensusResult(
                submission_id=submission_id,
                data_hash=self.submissions[submission_id].data_hash,
                verifications=total_verifications,
                required_verifications=self.min_verifications,
                consensus_reached=True,
                final_status='verified',
                confidence_level=confidence_level
            )
        elif rejected_count >= self.min_verifications:
            return ConsensusResult(
                submission_id=submission_id,
                data_hash=self.submissions[submission_id].data_hash,
                verifications=total_verifications,
                required_verifications=self.min_verifications,
                consensus_reached=True,
                final_status='rejected',
                confidence_level=confidence_level
            )
            
        # No consensus yet
        return None
        
    def _update_network_stats(self, consensus_result: ConsensusResult):
        """Update network statistics based on consensus result"""
        if consensus_result.final_status == 'verified':
            self.network_stats['verified_submissions'] += 1
        elif consensus_result.final_status == 'rejected':
            self.network_stats['rejected_submissions'] += 1
            
    def get_pending_submissions(self, verifier_id: str) -> List[Submission]:
        """Get submissions pending verification for a verifier"""
        pending = []
        
        with self.lock:
            for submission_id, verifications in self.verifications.items():
                # Check if verifier has pending verification for this submission
                verifier_has_verified = any(
                    v.verifier_id == verifier_id for v in verifications
                )
                
                if not verifier_has_verified:
                    # Check if submission is still pending consensus
                    if submission_id not in self.consensus_results:
                        pending.append(self.submissions[submission_id])
                        
        return pending
        
    def get_verifier_stats(self, verifier_id: str) -> Dict[str, Any]:
        """Get statistics for a verifier"""
        with self.lock:
            # Count verifications by this verifier
            verifier_verifications = []
            for verifications in self.verifications.values():
                verifier_verifications.extend([
                    v for v in verifications if v.verifier_id == verifier_id
                ])
                
            # Count verified vs rejected
            verified_count = sum(1 for v in verifier_verifications if v.status == 'verified')
            rejected_count = sum(1 for v in verifier_verifications if v.status == 'rejected')
            total_count = len(verifier_verifications)
            
            return {
                'verifier_id': verifier_id,
                'total_verifications': total_count,
                'verified_count': verified_count,
                'rejected_count': rejected_count,
                'accuracy_rate': (verified_count / total_count * 100) if total_count > 0 else 0,
                'reputation_score': self.reputation_scores.get(verifier_id, 0.0)
            }
            
    def get_network_stats(self) -> Dict[str, Any]:
        """Get overall network statistics"""
        with self.lock:
            return self.network_stats.copy()
            
    def get_consensus_result(self, submission_id: str) -> Optional[ConsensusResult]:
        """Get consensus result for a submission"""
        with self.lock:
            return self.consensus_results.get(submission_id)
            
    def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old submissions and verifications"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        with self.lock:
            # Remove old submissions
            old_submissions = [
                sid for sid, submission in self.submissions.items()
                if submission.submission_time < cutoff_time
            ]
            
            for sid in old_submissions:
                del self.submissions[sid]
                if sid in self.verifications:
                    del self.verifications[sid]
                if sid in self.consensus_results:
                    del self.consensus_results[sid]
                    
            print(f"Cleaned up {len(old_submissions)} old submissions")

# Example usage
if __name__ == "__main__":
    # Initialize verification network
    network = VerificationNetwork(min_verifications=3)
    
    # Register some verifiers
    for i in range(10):
        network.register_verifier(f"verifier_{i}", {"type": "volunteer"})
        
    # Create a sample submission
    sample_data = {
        "type": "statement",
        "content": "This is a test statement",
        "source": "test_source"
    }
    
    submission = Submission(
        id="test_submission_1",
        data=sample_data,
        signature="test_signature",
        volunteer_id="volunteer_1",
        submission_time=time.time(),
        data_hash=hashlib.sha256(json.dumps(sample_data, sort_keys=True).encode()).hexdigest(),
        public_key="test_public_key"
    )
    
    # Submit for verification
    network.submit_for_verification(submission)
    
    # Simulate verifications
    for i in range(3):
        verification = Verification(
            submission_id="test_submission_1",
            verifier_id=f"verifier_{i}",
            verification_time=time.time(),
            signature=f"verification_signature_{i}",
            status="verified",
            confidence_score=0.95
        )
        network.submit_verification(verification)
        
    # Check consensus result
    result = network.get_consensus_result("test_submission_1")
    if result:
        print(f"Consensus result: {result}")
        
    # Get network stats
    stats = network.get_network_stats()
    print(f"Network stats: {stats}")