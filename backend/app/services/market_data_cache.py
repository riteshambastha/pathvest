"""
Market Data Cache Service using Redis/In-Memory Cache
Implements caching layer for AlphaVantage data to reduce API calls
"""

import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, date, timedelta
from app.core.config import settings

# Try to import Redis, fall back to in-memory cache if not available
try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class MarketDataCache:
    """Cache service for market data with TTL support"""
    
    def __init__(self):
        """Initialize cache"""
        self.redis_client = None
        self.memory_cache: Dict[str, tuple[Any, datetime]] = {}
        self.ttl_seconds = settings.REDIS_CACHE_TTL_SECONDS
        
        if REDIS_AVAILABLE and settings.REDIS_URL:
            # Will connect to Redis when needed
            self.use_redis = True
        else:
            # Fall back to in-memory cache
            self.use_redis = False
            print("Using in-memory cache (Redis not available)")
    
    async def _get_redis_client(self):
        """Get or create Redis client"""
        if not self.use_redis:
            return None
        
        if self.redis_client is None:
            try:
                self.redis_client = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                print(f"Failed to connect to Redis: {e}")
                self.use_redis = False
                return None
        
        return self.redis_client
    
    def _make_key(self, namespace: str, identifier: str, *args) -> str:
        """Create cache key"""
        parts = [namespace, identifier] + [str(arg) for arg in args]
        return ":".join(parts)
    
    async def get(self, namespace: str, identifier: str, *args) -> Optional[Any]:
        """Get value from cache"""
        key = self._make_key(namespace, identifier, *args)
        
        if self.use_redis:
            redis = await self._get_redis_client()
            if redis:
                try:
                    value = await redis.get(key)
                    if value:
                        return json.loads(value)
                except Exception as e:
                    print(f"Redis get error: {e}")
        
        # Fall back to memory cache
        if key in self.memory_cache:
            value, expiry = self.memory_cache[key]
            if datetime.now() < expiry:
                return value
            else:
                # Expired, remove it
                del self.memory_cache[key]
        
        return None
    
    async def set(
        self,
        namespace: str,
        identifier: str,
        value: Any,
        *args,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with TTL"""
        key = self._make_key(namespace, identifier, *args)
        ttl_to_use = ttl or self.ttl_seconds
        
        if self.use_redis:
            redis = await self._get_redis_client()
            if redis:
                try:
                    await redis.setex(
                        key,
                        ttl_to_use,
                        json.dumps(value)
                    )
                    return True
                except Exception as e:
                    print(f"Redis set error: {e}")
        
        # Fall back to memory cache
        expiry = datetime.now() + timedelta(seconds=ttl_to_use)
        self.memory_cache[key] = (value, expiry)
        
        # Clean up expired entries periodically
        if len(self.memory_cache) % 100 == 0:
            self._cleanup_memory_cache()
        
        return True
    
    async def delete(self, namespace: str, identifier: str, *args) -> bool:
        """Delete value from cache"""
        key = self._make_key(namespace, identifier, *args)
        
        if self.use_redis:
            redis = await self._get_redis_client()
            if redis:
                try:
                    await redis.delete(key)
                except Exception as e:
                    print(f"Redis delete error: {e}")
        
        # Also delete from memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        return True
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self.memory_cache.items()
            if now >= expiry
        ]
        for key in expired_keys:
            del self.memory_cache[key]
    
    async def get_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached daily bars for symbol and date range"""
        return await self.get(
            "market_data",
            "daily_bars",
            symbol,
            start_date.isoformat(),
            end_date.isoformat()
        )
    
    async def set_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        bars: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache daily bars for symbol and date range"""
        return await self.set(
            "market_data",
            "daily_bars",
            bars,
            symbol,
            start_date.isoformat(),
            end_date.isoformat(),
            ttl=ttl
        )
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached quote for symbol"""
        return await self.get("market_data", "quote", symbol)
    
    async def set_quote(
        self,
        symbol: str,
        quote: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache quote for symbol (shorter TTL - quotes change frequently)"""
        # Default to 5 minutes for quotes
        ttl_to_use = ttl or 300
        return await self.set("market_data", "quote", quote, symbol, ttl=ttl_to_use)
    
    async def get_company_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached company overview"""
        return await self.get("market_data", "overview", symbol)
    
    async def set_company_overview(
        self,
        symbol: str,
        overview: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache company overview (longer TTL - fundamentals change slowly)"""
        # Default to 7 days for company overview
        ttl_to_use = ttl or (7 * 24 * 3600)
        return await self.set("market_data", "overview", overview, symbol, ttl=ttl_to_use)
    
    async def clear_all(self) -> bool:
        """Clear all cached data (use with caution)"""
        if self.use_redis:
            redis = await self._get_redis_client()
            if redis:
                try:
                    await redis.flushdb()
                except Exception as e:
                    print(f"Redis flushdb error: {e}")
        
        self.memory_cache.clear()
        return True
    
    async def close(self):
        """Close connections"""
        if self.redis_client:
            await self.redis_client.close()


# Singleton instance
_cache_service = None


def get_cache_service() -> MarketDataCache:
    """Get or create cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = MarketDataCache()
    return _cache_service

