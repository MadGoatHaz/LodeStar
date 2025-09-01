import json
import time
import uuid
from collections import defaultdict
import ipfshttpclient

class FlaggingService:
    def __init__(self, flags_file='flags.json'):
        """Initialize flagging service"""
        self.flags_file = flags_file
        self.flags = self.load_flags()
        self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        self.flag_counts = defaultdict(int)
        self.user_flag_counts = defaultdict(int)
        
        # Load existing flag counts
        self._rebuild_flag_counts()
        
    def load_flags(self):
        """Load flags from JSON file"""
        try:
            with open(self.flags_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error loading flags: {e}")
            return []
            
    def save_flags(self):
        """Save flags to JSON file"""
        try:
            with open(self.flags_file, 'w') as f:
                json.dump(self.flags, f, indent=2)
        except Exception as e:
            print(f"Error saving flags: {e}")
            
    def _rebuild_flag_counts(self):
        """Rebuild flag counts from existing flags"""
        self.flag_counts.clear()
        self.user_flag_counts.clear()
        
        for flag in self.flags:
            if flag.get('status') == 'pending':
                self.flag_counts[flag['ipfs_hash']] += 1
                self.user_flag_counts[flag['user_id']] += 1
                
    def submit_flag(self, ipfs_hash, reason, description="", user_id=None):
        """Submit a flag for content"""
        # Generate user ID if not provided
        if not user_id:
            user_id = f"anon_{uuid.uuid4().hex[:8]}"
            
        # Check rate limiting (max 10 flags per user per hour)
        if self.user_flag_counts[user_id] >= 10:
            # Check if user has flags older than 1 hour
            recent_flags = [
                f for f in self.flags 
                if f['user_id'] == user_id and 
                (time.time() - f['timestamp']) < 3600
            ]
            if len(recent_flags) >= 10:
                return {
                    'error': 'Rate limit exceeded. Maximum 10 flags per hour.',
                    'status': 'error'
                }
                
        # Check for duplicate flags from same user
        for flag in self.flags:
            if (flag['ipfs_hash'] == ipfs_hash and 
                flag['user_id'] == user_id and 
                flag['status'] == 'pending'):
                return {
                    'error': 'You have already flagged this content.',
                    'status': 'error'
                }
                
        # Create flag record
        flag_record = {
            'id': str(uuid.uuid4()),
            'ipfs_hash': ipfs_hash,
            'reason': reason,
            'description': description,
            'user_id': user_id,
            'timestamp': time.time(),
            'status': 'pending'
        }
        
        # Add to flags list
        self.flags.append(flag_record)
        
        # Update counts
        self.flag_counts[ipfs_hash] += 1
        self.user_flag_counts[user_id] += 1
        
        # Save to file
        self.save_flags()
        
        return {
            'status': 'success',
            'message': 'Flag submitted successfully',
            'flag_id': flag_record['id']
        }
        
    def get_flags_for_content(self, ipfs_hash):
        """Get all flags for specific content"""
        content_flags = [
            flag for flag in self.flags 
            if flag['ipfs_hash'] == ipfs_hash
        ]
        return content_flags
        
    def get_all_flags(self, status=None):
        """Get all flags, optionally filtered by status"""
        if status:
            return [flag for flag in self.flags if flag.get('status') == status]
        return self.flags
        
    def get_flag_counts(self, ipfs_hash=None):
        """Get flag counts, optionally for specific content"""
        if ipfs_hash:
            return self.flag_counts.get(ipfs_hash, 0)
        return dict(self.flag_counts)
        
    def update_flag_status(self, flag_id, status, moderator_id=None):
        """Update flag status (moderator action)"""
        for flag in self.flags:
            if flag['id'] == flag_id:
                flag['status'] = status
                flag['moderator_id'] = moderator_id
                flag['resolved_timestamp'] = time.time()
                
                # Update counts
                if status != 'pending':
                    self.flag_counts[flag['ipfs_hash']] -= 1
                    if self.flag_counts[flag['ipfs_hash']] < 0:
                        self.flag_counts[flag['ipfs_hash']] = 0
                    self.user_flag_counts[flag['user_id']] -= 1
                    if self.user_flag_counts[flag['user_id']] < 0:
                        self.user_flag_counts[flag['user_id']] = 0
                
                self.save_flags()
                return {
                    'status': 'success',
                    'message': f'Flag status updated to {status}'
                }
                
        return {
            'error': 'Flag not found',
            'status': 'error'
        }
        
    def get_moderation_queue(self):
        """Get prioritized moderation queue"""
        # Get pending flags
        pending_flags = self.get_all_flags(status='pending')
        
        # Group by IPFS hash and count flags
        content_flags = defaultdict(list)
        for flag in pending_flags:
            content_flags[flag['ipfs_hash']].append(flag)
            
        # Create queue with flag counts
        queue = []
        for ipfs_hash, flags in content_flags.items():
            # Get content metadata from IPFS
            try:
                content = self.ipfs_client.get_json(ipfs_hash)
            except:
                content = {'type': 'unknown', 'title': 'Unknown Content'}
                
            queue.append({
                'ipfs_hash': ipfs_hash,
                'flag_count': len(flags),
                'flags': flags,
                'content': content,
                'priority': len(flags)  # Simple priority based on flag count
            })
            
        # Sort by priority (highest first)
        queue.sort(key=lambda x: x['priority'], reverse=True)
        
        return queue

# Example usage
if __name__ == "__main__":
    flagging_service = FlaggingService()
    
    # Example: submit a flag
    # result = flagging_service.submit_flag(
    #     ipfs_hash="QmExampleHash",
    #     reason="inappropriate",
    #     description="Contains inappropriate content",
    #     user_id="user123"
    # )
    # print(result)