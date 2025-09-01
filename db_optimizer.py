import sqlite3
import time
import threading
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class QueryStat:
    query: str
    execution_time: float
    rows_returned: int
    timestamp: float
    cached: bool = False
    optimized: bool = False

class DatabaseOptimizer:
    def __init__(self, db_path: str, max_connections: int = 10):
        """Initialize database optimizer with connection pooling"""
        self.db_path = db_path
        self.max_connections = max_connections
        self.connection_pool = []
        self.lock = threading.Lock()
        self.query_stats = []
        self.indexes = {}
        self.cache = {}
        
        # Initialize connection pool
        self._initialize_pool()
        
    def _initialize_pool(self):
        """Initialize connection pool"""
        for _ in range(self.max_connections):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connection_pool.append(conn)
            
    @contextmanager
    def get_connection(self):
        """Get database connection from pool"""
        conn = None
        try:
            with self.lock:
                if self.connection_pool:
                    conn = self.connection_pool.pop()
                else:
                    # Create new connection if pool is empty
                    conn = sqlite3.connect(self.db_path, check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    
            yield conn
        finally:
            if conn:
                with self.lock:
                    if len(self.connection_pool) < self.max_connections:
                        self.connection_pool.append(conn)
                    else:
                        conn.close()
                        
    def execute_query(self, query: str, params: tuple = (), use_cache: bool = True) -> List[Dict]:
        """Execute query with optimization and caching"""
        # Generate cache key
        cache_key = f"{query}:{params}" if use_cache else None
        
        # Check cache first
        if use_cache and cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < 300:  # 5 minute cache
                return cached_result
                
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                result = [dict(row) for row in rows]
                
                execution_time = time.time() - start_time
                
                # Store in cache
                if use_cache and cache_key:
                    self.cache[cache_key] = (result, time.time())
                    
                # Record query statistics
                self.query_stats.append(QueryStat(
                    query=query,
                    execution_time=execution_time,
                    rows_returned=len(result),
                    timestamp=time.time(),
                    cached=False
                ))
                
                return result
                
        except Exception as e:
            print(f"Database query error: {e}")
            return []
            
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute multiple queries with optimization"""
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                
                execution_time = time.time() - start_time
                
                # Record query statistics
                self.query_stats.append(QueryStat(
                    query=query,
                    execution_time=execution_time,
                    rows_returned=len(params_list),
                    timestamp=time.time(),
                    optimized=True
                ))
                
                return cursor.rowcount
                
        except Exception as e:
            print(f"Database bulk insert error: {e}")
            return 0
            
    def create_index(self, table: str, columns: List[str], index_name: Optional[str] = None):
        """Create index on table columns"""
        if not index_name:
            index_name = f"idx_{table}_{'_'.join(columns)}"
            
        columns_str = ", ".join(columns)
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({columns_str})"
        
        try:
            with self.get_connection() as conn:
                conn.execute(query)
                conn.commit()
                self.indexes[index_name] = {
                    'table': table,
                    'columns': columns,
                    'created_at': time.time()
                }
                print(f"Index {index_name} created on {table}({columns_str})")
        except Exception as e:
            print(f"Error creating index: {e}")
            
    def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze query performance statistics"""
        if not self.query_stats:
            return {"message": "No query statistics available"}
            
        # Group statistics by query
        query_performance = defaultdict(list)
        for stat in self.query_stats:
            query_performance[stat.query].append(stat)
            
        # Calculate performance metrics
        performance_report = {}
        for query, stats in query_performance.items():
            total_time = sum(s.execution_time for s in stats)
            avg_time = total_time / len(stats)
            total_rows = sum(s.rows_returned for s in stats)
            avg_rows = total_rows / len(stats)
            
            performance_report[query] = {
                'execution_count': len(stats),
                'total_time': round(total_time, 4),
                'average_time': round(avg_time, 4),
                'total_rows': total_rows,
                'average_rows': round(avg_rows, 2),
                'cached_queries': sum(1 for s in stats if s.cached),
                'optimized_queries': sum(1 for s in stats if s.optimized)
            }
            
        return performance_report
        
    def get_slow_queries(self, threshold: float = 1.0) -> List[QueryStat]:
        """Get queries that exceed execution time threshold"""
        return [stat for stat in self.query_stats if stat.execution_time > threshold]
        
    def optimize_table(self, table: str):
        """Optimize table performance"""
        try:
            with self.get_connection() as conn:
                # Analyze table
                conn.execute(f"ANALYZE {table}")
                
                # Rebuild table statistics
                conn.execute("ANALYZE")
                
                conn.commit()
                print(f"Table {table} optimized")
        except Exception as e:
            print(f"Error optimizing table: {e}")
            
    def get_connection_pool_stats(self) -> Dict[str, int]:
        """Get connection pool statistics"""
        return {
            'available_connections': len(self.connection_pool),
            'max_connections': self.max_connections,
            'used_connections': self.max_connections - len(self.connection_pool)
        }
        
    def clear_cache(self):
        """Clear query cache"""
        self.cache.clear()
        print("Query cache cleared")
        
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cached_queries': len(self.cache),
            'cache_size_mb': sum(len(str(v)) for v in self.cache.values()) / (1024 * 1024)
        }
        
    def close_all_connections(self):
        """Close all database connections"""
        with self.lock:
            for conn in self.connection_pool:
                try:
                    conn.close()
                except:
                    pass
            self.connection_pool.clear()

# Example usage
if __name__ == "__main__":
    # Initialize database optimizer
    db_optimizer = DatabaseOptimizer("example.db")
    
    # Create example table
    with db_optimizer.get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
    # Create index
    db_optimizer.create_index("users", ["email"])
    
    # Insert some data
    db_optimizer.execute_many(
        "INSERT OR IGNORE INTO users (name, email) VALUES (?, ?)",
        [("Alice", "alice@example.com"), ("Bob", "bob@example.com")]
    )
    
    # Query with caching
    users = db_optimizer.execute_query(
        "SELECT * FROM users WHERE email = ?", 
        ("alice@example.com",)
    )
    print("Users:", users)
    
    # Analyze performance
    performance = db_optimizer.analyze_query_performance()
    print("Performance report:", performance)
    
    # Close connections
    db_optimizer.close_all_connections()