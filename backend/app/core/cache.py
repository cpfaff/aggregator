from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Any

# SimpleCache for in-memory caching
class SimpleCache:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key):
        if key in self.cache:
            value, expires_at = self.cache[key]
            if expires_at > datetime.utcnow():
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key, value, ttl_seconds=None):
        ttl = ttl_seconds or self.ttl_seconds
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        self.cache[key] = (value, expires_at)

    def invalidate(self, prefix=None):
        if prefix:
            keys_to_remove = [
                key for key in self.cache.keys() if key.startswith(prefix)
            ]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()

# Global cache instance
from app.core.config import settings
cache = SimpleCache(ttl_seconds=settings.CACHE_EXPIRE_SECONDS)


def cache_response(prefix, ttl_seconds=None):
    """Decorator to cache function responses with prefix for key generation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not settings.CACHE_ENABLED:
                return await func(*args, **kwargs)

            # Generate a cache key based on function name, args, and kwargs
            key_parts = [prefix, func.__name__]
            # Skip Request and AsyncSession objects
            from fastapi import Request
            from sqlalchemy.ext.asyncio import AsyncSession
            key_parts.extend(
                [
                    str(arg)
                    for arg in args
                    if not isinstance(arg, Request)
                    and not isinstance(arg, AsyncSession)
                ]
            )
            for k, v in sorted(kwargs.items()):
                if k not in ["db", "request", "current_user"]:
                    key_parts.append(f"{k}:{v}")
            cache_key = ":".join(key_parts)

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix):
    """Invalidate cache entries with specified prefix"""
    cache.invalidate(prefix)


# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self):
        self._requests = {}
    
    def is_allowed(self, identifier: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            identifier: Unique identifier (e.g., IP, user ID)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            bool: True if request is allowed
        """
        import time
        current_time = time.time()
        window_start = current_time - window
        
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        # Clean old requests
        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self._requests[identifier]) >= limit:
            return False
        
        # Add current request
        self._requests[identifier].append(current_time)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()
