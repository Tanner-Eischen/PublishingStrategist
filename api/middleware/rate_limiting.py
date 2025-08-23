"""Rate limiting middleware for API endpoints."""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds (default: 1 hour)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client."""
        now = time.time()
        client_requests = self.requests[client_id]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) >= self.max_requests:
            return False
        
        # Add current request
        client_requests.append(now)
        return True
    
    def get_reset_time(self, client_id: str) -> Optional[float]:
        """Get time when rate limit resets for client."""
        client_requests = self.requests[client_id]
        if not client_requests:
            return None
        return client_requests[0] + self.window_seconds


# Global rate limiters for different endpoint types
rate_limiters = {
    "niche_discovery": RateLimiter(max_requests=10, window_seconds=3600),  # 10 per hour
    "trend_validation": RateLimiter(max_requests=20, window_seconds=3600),  # 20 per hour
    "general": RateLimiter(max_requests=100, window_seconds=3600),  # 100 per hour
}


async def rate_limit_middleware(request: Request, call_next, limiter_type: str = "general"):
    """Rate limiting middleware."""
    # Get client identifier (IP address)
    client_ip = request.client.host if request.client else "unknown"
    
    # Check rate limit
    limiter = rate_limiters.get(limiter_type, rate_limiters["general"])
    
    if not limiter.is_allowed(client_ip):
        reset_time = limiter.get_reset_time(client_ip)
        reset_timestamp = int(reset_time) if reset_time else int(time.time() + limiter.window_seconds)
        
        logger.warning(f"Rate limit exceeded for {client_ip} on {limiter_type}")
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {limiter.max_requests} per {limiter.window_seconds} seconds",
                "retry_after": reset_timestamp - int(time.time()),
                "reset_time": reset_timestamp
            },
            headers={
                "X-RateLimit-Limit": str(limiter.max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_timestamp),
                "Retry-After": str(reset_timestamp - int(time.time()))
            }
        )
    
    # Add rate limit headers to response
    response = await call_next(request)
    
    # Calculate remaining requests
    client_requests = limiter.requests[client_ip]
    remaining = max(0, limiter.max_requests - len(client_requests))
    reset_time = limiter.get_reset_time(client_ip)
    reset_timestamp = int(reset_time) if reset_time else int(time.time() + limiter.window_seconds)
    
    response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_timestamp)
    
    return response


def get_rate_limiter(limiter_type: str = "general") -> RateLimiter:
    """Get rate limiter by type."""
    return rate_limiters.get(limiter_type, rate_limiters["general"])