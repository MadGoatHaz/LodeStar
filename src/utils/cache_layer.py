import redis
import json
import hashlib
import time
from functools import wraps
from typing import Any, Optional, Callable

class CacheLayer:
    def __init__(self, host='localhost', port=6379, db=0, default_ttl=3600):
        """Initialize cache layer with Redis connection"""
        self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.default_ttl = default_ttl
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        # Create a hash of the arguments to ensure consistent key generation
        key_data = str(args) + str(sorted(kwargs.items()))
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis_client.get(key)
            if value:
                self.stats['hits'] += 1
                return json.loads(value)
            else:
                self.stats['misses'] += 1
                return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
            
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            serialized_value = json.dumps(value, default=str)
            ttl = ttl or self.default_ttl
            result = self.redis_client.setex(key, ttl, serialized_value)
            if result:
                self.stats['sets'] += 1
            return result
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
            
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            result = self.redis_client.delete(key)
            if result:
                self.stats['deletes'] += 1
            return result > 0
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
            
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                result = self.redis_client.delete(*keys)
                self.stats['deletes'] += result
                return result
            return 0
        except Exception as e:
            print(f"Cache pattern invalidation error: {e}")
            return 0
            
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests
        }
        
    def clear_stats(self):
        """Clear cache statistics"""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
    def cache(self, prefix: str, ttl: Optional[int] = None):
        """Decorator for caching function results"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                key = self.generate_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_result = self.get(key)
                if cached_result is not None:
                    return cached_result
                    
                # If not in cache, call function
                result = func(*args, **kwargs)
                
                # Store result in cache
                self.set(key, result, ttl)
                
                return result
            return wrapper
        return decorator
        
    def warm_cache(self, key: str, func: Callable, *args, **kwargs) -> Any:
        """Pre-populate cache with function result"""
        result = func(*args, **kwargs)
        self.set(key, result)
        return result
        
    def get_cache_size(self) -> int:
        """Get approximate number of keys in cache"""
        try:
            return self.redis_client.dbsize()
        except Exception as e:
            print(f"Error getting cache size: {e}")
            return 0
            
    def flush_cache(self) -> bool:
        """Clear all cache entries"""
        try:
            self.redis_client.flushdb()
            self.clear_stats()
            return True
        except Exception as e:
            print(f"Error flushing cache: {e}")
            return False

# Example usage
if __name__ == "__main__":
    # Initialize cache
    cache = CacheLayer()
    
    # Example function with caching
    @cache.cache(prefix="user_data", ttl=1800)
    def get_user_data(user_id):
        # Simulate database call
        time.sleep(0.1)  # Simulate delay
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com"
        }
    
    # Example usage
    # First call will populate cache
    user1 = get_user_data(123)
    print("First call:", user1)
    
    # Second call will use cache
    user2 = get_user_data(123)
    print("Second call:", user2)
    
    # Check cache stats
    print("Cache stats:", cache.get_stats())