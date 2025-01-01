from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import time
from fastapi import Request
import logging
from collections import defaultdict
import asyncio
from threading import Lock

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Thread-safe rate limiter implementation for FastAPI with request-based limiting
    and configurable windows.
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        time_window: int = 3600,
        cleanup_interval: int = 3600
    ):
        """
        Initialize rate limiter with configurable requests and time window.
        
        Args:
            max_requests (int): Maximum number of requests allowed in the time window
            time_window (int): Time window in seconds
            cleanup_interval (int): How often to clean up expired entries (seconds)
        """
        if max_requests <= 0 or time_window <= 0:
            raise ValueError("max_requests and time_window must be positive")
            
        self.max_requests = max_requests
        self.time_window = time_window
        self._buckets: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._last_cleanup = time.time()
        self._cleanup_interval = cleanup_interval
        self._lock = Lock()  # Thread safety for bucket operations
        
    def _generate_key(self, request: Request, key_prefix: str) -> str:
        """
        Generate a unique key for rate limiting based on request and prefix.
        
        Args:
            request (Request): FastAPI request object
            key_prefix (str): Prefix for the rate limit key
            
        Returns:
            str: Unique rate limit key
        """
        # Get client IP with better proxy handling
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
            
        # Additional request properties for more granular limiting
        user_agent = request.headers.get('User-Agent', 'unknown')
        
        # Create a composite key
        return f"{key_prefix}:{client_ip}:{hash(user_agent)}"
        
    def _cleanup_expired(self) -> None:
        """Remove expired rate limit entries to prevent memory leaks."""
        current_time = time.time()
        
        # Only cleanup if enough time has passed
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
            
        with self._lock:
            # Remove expired entries
            expired_time = current_time - self.time_window
            expired_keys = [
                key for key, bucket in self._buckets.items()
                if bucket.get('reset_time', 0) < expired_time
            ]
            
            for key in expired_keys:
                del self._buckets[key]
                
            self._last_cleanup = current_time
        
    async def check_rate_limit(
        self,
        request: Request,
        key_prefix: str,
        max_requests: Optional[int] = None,
        time_window: Optional[int] = None
    ) -> bool:
        """
        Check if a request is allowed based on rate limiting rules.
        
        Args:
            request (Request): FastAPI request object
            key_prefix (str): Prefix for the rate limit key
            max_requests (Optional[int]): Override default max requests
            time_window (Optional[int]): Override default time window
            
        Returns:
            bool: True if request is allowed, False if rate limit exceeded
        """
        try:
            self._cleanup_expired()
            
            # Use provided values or defaults
            limit = max(1, max_requests or self.max_requests)
            window = max(1, time_window or self.time_window)
            
            # Generate unique key for this request
            key = self._generate_key(request, key_prefix)
            current_time = time.time()
            
            with self._lock:
                # Get or create bucket for this key
                bucket = self._buckets[key]
                
                # Initialize new bucket if needed
                if not bucket:
                    bucket.update({
                        'count': 0,
                        'reset_time': current_time + window,
                        'last_request': current_time
                    })
                    
                # Reset if time window has passed
                if current_time > bucket['reset_time']:
                    bucket.update({
                        'count': 0,
                        'reset_time': current_time + window,
                        'last_request': current_time
                    })
                    
                # Check if rate limit is exceeded
                if bucket['count'] >= limit:
                    logger.warning(f"Rate limit exceeded for {key}")
                    return False
                    
                # Update bucket
                bucket['count'] += 1
                bucket['last_request'] = current_time
                
                return True
                
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}", exc_info=True)
            # On error, allow the request but log the issue
            return True
            
    def get_limit_headers(self, request: Request, key_prefix: str) -> Dict[str, str]:
        """
        Get rate limit headers for response.
        """
        key = self._generate_key(request, key_prefix)
        
        with self._lock:
            bucket = self._buckets.get(key, {})
            
            if not bucket:
                return {
                    'X-RateLimit-Limit': str(self.max_requests),
                    'X-RateLimit-Remaining': str(self.max_requests),
                    'X-RateLimit-Reset': str(int(time.time() + self.time_window))
                }
                
            remaining = max(0, self.max_requests - bucket['count'])
            
            return {
                'X-RateLimit-Limit': str(self.max_requests),
                'X-RateLimit-Remaining': str(remaining),
                'X-RateLimit-Reset': str(int(bucket['reset_time']))
            }

    def reset(self, request: Request, key_prefix: str) -> None:
        """
        Reset rate limit for a specific key.
        """
        key = self._generate_key(request, key_prefix)
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]