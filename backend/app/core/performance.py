"""
Performance optimization configurations and utilities for PathVest.
"""

from functools import lru_cache, wraps
from typing import Any, Callable
import time
import asyncio
from redis import Redis
import pickle
import hashlib


class CacheManager:
    """Centralized cache management with Redis backend."""
    
    def __init__(self, redis_client: Redis, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Any:
        """Get value from cache."""
        data = self.redis.get(key)
        if data:
            return pickle.loads(data)
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        serialized = pickle.dumps(value)
        return self.redis.setex(key, ttl, serialized)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        return self.redis.delete(key) > 0
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        keys = self.redis.keys(pattern)
        if keys:
            return self.redis.delete(*keys)
        return 0
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments."""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"


def cache_result(ttl: int = 3600, key_prefix: str = None):
    """
    Decorator to cache function results in Redis.
    
    Usage:
        @cache_result(ttl=3600, key_prefix="market_data")
        def get_market_data(ticker: str, date: str):
            return fetch_data(ticker, date)
    """
    def decorator(func: Callable) -> Callable:
        prefix = key_prefix or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            from app.core.config import settings
            from app.db.session import get_redis
            
            redis = get_redis()
            cache_mgr = CacheManager(redis, ttl)
            
            cache_key = cache_mgr.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached = cache_mgr.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache_mgr.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            from app.core.config import settings
            from app.db.session import get_redis
            
            redis = get_redis()
            cache_mgr = CacheManager(redis, ttl)
            
            cache_key = cache_mgr.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached = cache_mgr.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache_mgr.set(cache_key, result, ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        print(f"⏱️  {func.__name__} took {duration:.2f}s")
        return result
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"⏱️  {func.__name__} took {duration:.2f}s")
        return result
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class BatchProcessor:
    """Batch processing utility for efficient bulk operations."""
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
    
    def process_in_batches(self, items: list, processor: Callable) -> list:
        """Process items in batches."""
        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = processor(batch)
            results.extend(batch_results)
        return results
    
    async def process_in_batches_async(
        self,
        items: list,
        processor: Callable,
        max_concurrent: int = 5
    ) -> list:
        """Process items in batches asynchronously with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_batch(batch):
            async with semaphore:
                return await processor(batch)
        
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        results = []
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results


class QueryOptimizer:
    """Database query optimization utilities."""
    
    @staticmethod
    def chunk_query(query, chunk_size: int = 10000):
        """
        Generator to yield query results in chunks for memory efficiency.
        
        Usage:
            for chunk in QueryOptimizer.chunk_query(session.query(Model), 1000):
                process(chunk)
        """
        offset = 0
        while True:
            chunk = query.limit(chunk_size).offset(offset).all()
            if not chunk:
                break
            yield chunk
            offset += chunk_size
    
    @staticmethod
    def batch_insert(session, model_class, records: list, batch_size: int = 1000):
        """Bulk insert records in batches."""
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            session.bulk_insert_mappings(model_class, batch)
            session.commit()


# Performance monitoring
class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics = {}
    
    def record_execution_time(self, operation: str, duration: float):
        """Record execution time for an operation."""
        if operation not in self.metrics:
            self.metrics[operation] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }
        
        metrics = self.metrics[operation]
        metrics['count'] += 1
        metrics['total_time'] += duration
        metrics['min_time'] = min(metrics['min_time'], duration)
        metrics['max_time'] = max(metrics['max_time'], duration)
    
    def get_stats(self, operation: str = None):
        """Get performance statistics."""
        if operation:
            if operation in self.metrics:
                metrics = self.metrics[operation]
                return {
                    'operation': operation,
                    'count': metrics['count'],
                    'avg_time': metrics['total_time'] / metrics['count'],
                    'min_time': metrics['min_time'],
                    'max_time': metrics['max_time'],
                    'total_time': metrics['total_time']
                }
            return None
        
        return {
            op: self.get_stats(op)
            for op in self.metrics.keys()
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()

