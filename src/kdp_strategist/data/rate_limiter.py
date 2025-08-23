"""Advanced rate limiting system for Keepa API client.

This module provides:
- Token bucket algorithm with burst capacity
- Sliding window rate limiting
- Concurrent request handling with queuing
- Rate limit status reporting and monitoring
- Intelligent wait time calculation
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from threading import Lock
import threading

from ..exceptions import KeepaRateLimitError
from ..exceptions import KeepaErrorLogger


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting system."""
    max_requests_per_minute: int = 100
    burst_capacity: Optional[int] = None  # Defaults to 2x max_requests
    time_window_seconds: int = 60
    sliding_window_size: int = 10  # Number of sub-windows for sliding window
    max_concurrent_requests: int = 10
    queue_timeout_seconds: int = 300  # 5 minutes
    enable_monitoring: bool = True


@dataclass
class RateLimitStatus:
    """Current rate limit status information."""
    current_tokens: float
    max_tokens: int
    requests_in_window: int
    max_requests: int
    time_window_seconds: int
    utilization_percentage: float
    burst_capacity: int
    queue_size: int
    active_requests: int
    estimated_wait_time: float
    last_request_time: Optional[datetime] = None
    requests_per_second: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "requests_in_window": self.requests_in_window,
            "max_requests": self.max_requests,
            "time_window_seconds": self.time_window_seconds,
            "utilization_percentage": self.utilization_percentage,
            "burst_capacity": self.burst_capacity,
            "queue_size": self.queue_size,
            "active_requests": self.active_requests,
            "estimated_wait_time": self.estimated_wait_time,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "requests_per_second": self.requests_per_second
        }


@dataclass
class RequestMetrics:
    """Metrics for individual request tracking."""
    timestamp: datetime
    tokens_used: int
    wait_time: float = 0.0
    queue_time: float = 0.0
    success: bool = True


class TokenBucket:
    """Token bucket implementation for rate limiting with burst capacity."""
    
    def __init__(self, capacity: int, refill_rate: float, initial_tokens: Optional[int] = None):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens in bucket
            refill_rate: Tokens added per second
            initial_tokens: Initial token count (defaults to capacity)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill = time.time()
        self._lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False otherwise
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_tokens(self) -> float:
        """Get current token count."""
        with self._lock:
            self._refill()
            return self.tokens
    
    def time_until_tokens(self, tokens: int) -> float:
        """Calculate time until specified tokens are available."""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for more accurate rate control."""
    
    def __init__(self, max_requests: int, window_size_seconds: int, sub_windows: int = 10):
        """Initialize sliding window rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_size_seconds: Size of the time window in seconds
            sub_windows: Number of sub-windows for sliding effect
        """
        self.max_requests = max_requests
        self.window_size = window_size_seconds
        self.sub_window_size = window_size_seconds / sub_windows
        self.sub_windows = sub_windows
        self.request_counts = deque([0] * sub_windows, maxlen=sub_windows)
        self.last_update = time.time()
        self._lock = Lock()
    
    def is_allowed(self, requests: int = 1) -> bool:
        """Check if request is allowed under sliding window limit."""
        with self._lock:
            self._update_windows()
            
            current_total = sum(self.request_counts)
            if current_total + requests <= self.max_requests:
                # Add to current sub-window (last one)
                self.request_counts[-1] += requests
                return True
            return False
    
    def _update_windows(self):
        """Update sub-windows based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Calculate how many sub-windows have passed
        sub_windows_passed = int(elapsed / self.sub_window_size)
        
        if sub_windows_passed > 0:
            # Shift windows and add new empty windows
            windows_to_add = min(sub_windows_passed, self.sub_windows)
            for _ in range(windows_to_add):
                self.request_counts.append(0)
            
            self.last_update = now
    
    def get_current_usage(self) -> int:
        """Get current request count in the sliding window."""
        with self._lock:
            self._update_windows()
            return sum(self.request_counts)
    
    def get_utilization(self) -> float:
        """Get current utilization percentage."""
        return (self.get_current_usage() / self.max_requests) * 100


class RequestQueue:
    """Queue for managing concurrent requests with timeout."""
    
    def __init__(self, max_size: int = 1000, timeout_seconds: int = 300):
        """Initialize request queue.
        
        Args:
            max_size: Maximum queue size
            timeout_seconds: Request timeout in queue
        """
        self.max_size = max_size
        self.timeout = timeout_seconds
        self.queue = asyncio.Queue(maxsize=max_size)
        self.active_requests = 0
        self._lock = asyncio.Lock()
    
    async def enqueue(self, request_id: str, tokens_needed: int = 1) -> Tuple[str, int]:
        """Add request to queue.
        
        Args:
            request_id: Unique identifier for request
            tokens_needed: Number of tokens needed
            
        Returns:
            Tuple of (request_id, tokens_needed)
            
        Raises:
            asyncio.QueueFull: If queue is full
        """
        try:
            await asyncio.wait_for(
                self.queue.put((request_id, tokens_needed, time.time())),
                timeout=self.timeout
            )
            return request_id, tokens_needed
        except asyncio.TimeoutError:
            raise KeepaRateLimitError(
                retry_after=self.timeout,
                current_usage=self.queue.qsize(),
                limit=self.max_size,
                details={"queue_timeout": True}
            )
    
    async def dequeue(self) -> Tuple[str, int, float]:
        """Remove request from queue.
        
        Returns:
            Tuple of (request_id, tokens_needed, enqueue_time)
        """
        return await self.queue.get()
    
    def size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()
    
    async def increment_active(self):
        """Increment active request counter."""
        async with self._lock:
            self.active_requests += 1
    
    async def decrement_active(self):
        """Decrement active request counter."""
        async with self._lock:
            self.active_requests = max(0, self.active_requests - 1)
    
    def get_active_count(self) -> int:
        """Get number of active requests."""
        return self.active_requests


class AdvancedRateLimiter:
    """Advanced rate limiting system with token bucket, sliding window, and queuing."""
    
    def __init__(self, config: RateLimitConfig):
        """Initialize advanced rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.error_logger = KeepaErrorLogger(self.logger)
        
        # Initialize token bucket
        burst_capacity = config.burst_capacity or (config.max_requests_per_minute * 2)
        refill_rate = config.max_requests_per_minute / 60.0  # tokens per second
        self.token_bucket = TokenBucket(burst_capacity, refill_rate)
        
        # Initialize sliding window limiter
        self.sliding_window = SlidingWindowRateLimiter(
            config.max_requests_per_minute,
            config.time_window_seconds,
            config.sliding_window_size
        )
        
        # Initialize request queue
        self.request_queue = RequestQueue(
            max_size=config.max_requests_per_minute * 2,  # 2x buffer
            timeout_seconds=config.queue_timeout_seconds
        )
        
        # Metrics tracking
        self.request_history: deque = deque(maxlen=1000)
        self.start_time = datetime.now()
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.total_queue_time = 0.0
        
        # Background task for processing queue
        self._queue_processor_task = None
        self._shutdown_event = asyncio.Event()
        
        if config.enable_monitoring:
            try:
                self._start_queue_processor()
            except RuntimeError:
                # No event loop running - queue processor will be started later
                pass
    
    def _start_queue_processor(self):
        """Start background task for processing request queue."""
        try:
            if self._queue_processor_task is None or self._queue_processor_task.done():
                self._queue_processor_task = asyncio.create_task(self._process_queue())
        except RuntimeError:
            # No event loop running - will be started when needed
            pass
    
    async def _process_queue(self):
        """Background task to process queued requests."""
        while not self._shutdown_event.is_set():
            try:
                # Check if we can process requests
                if (self.token_bucket.get_tokens() >= 1 and 
                    self.sliding_window.is_allowed(1) and
                    self.request_queue.size() > 0):
                    
                    # Process one request from queue
                    request_id, tokens_needed, enqueue_time = await self.request_queue.dequeue()
                    queue_time = time.time() - enqueue_time
                    
                    # Try to acquire tokens
                    if (self.token_bucket.consume(tokens_needed) and 
                        self.sliding_window.is_allowed(tokens_needed)):
                        
                        await self.request_queue.increment_active()
                        
                        # Record metrics
                        metrics = RequestMetrics(
                            timestamp=datetime.now(),
                            tokens_used=tokens_needed,
                            queue_time=queue_time
                        )
                        self.request_history.append(metrics)
                        self.total_queue_time += queue_time
                        
                        # Request can proceed (would be handled by caller)
                        self.logger.debug(f"Processed queued request {request_id}")
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1.0)
    
    async def acquire_permit(self, tokens_needed: int = 1, request_id: Optional[str] = None) -> None:
        """Acquire permission to make API request(s).
        
        Args:
            tokens_needed: Number of tokens needed for request
            request_id: Optional request identifier for tracking
            
        Raises:
            KeepaRateLimitError: If rate limit is exceeded and cannot wait
        """
        if request_id is None:
            request_id = f"req_{int(time.time() * 1000)}"
        
        start_time = time.time()
        
        # Try immediate acquisition
        if (self.token_bucket.consume(tokens_needed) and 
            self.sliding_window.is_allowed(tokens_needed)):
            
            # Success - record metrics
            wait_time = time.time() - start_time
            metrics = RequestMetrics(
                timestamp=datetime.now(),
                tokens_used=tokens_needed,
                wait_time=wait_time
            )
            self.request_history.append(metrics)
            self.total_requests += 1
            self.total_wait_time += wait_time
            
            return
        
        # Need to wait or queue
        wait_time = self._calculate_intelligent_wait_time(tokens_needed)
        
        if wait_time <= 5.0:  # Short wait - just sleep
            self.logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
            await asyncio.sleep(wait_time)
            
            # Try again after waiting
            if (self.token_bucket.consume(tokens_needed) and 
                self.sliding_window.is_allowed(tokens_needed)):
                
                total_wait = time.time() - start_time
                metrics = RequestMetrics(
                    timestamp=datetime.now(),
                    tokens_used=tokens_needed,
                    wait_time=total_wait
                )
                self.request_history.append(metrics)
                self.total_requests += 1
                self.total_wait_time += total_wait
                return
        
        # Long wait - use queue if available
        if self.request_queue.size() < self.request_queue.max_size:
            self.logger.info(f"Queueing request {request_id} (estimated wait: {wait_time:.1f}s)")
            
            try:
                await self.request_queue.enqueue(request_id, tokens_needed)
                
                # Wait for queue processing (simplified - in real implementation,
                # this would use events/callbacks)
                max_wait = self.config.queue_timeout_seconds
                waited = 0.0
                
                while waited < max_wait:
                    if (self.token_bucket.consume(tokens_needed) and 
                        self.sliding_window.is_allowed(tokens_needed)):
                        
                        total_wait = time.time() - start_time
                        metrics = RequestMetrics(
                            timestamp=datetime.now(),
                            tokens_used=tokens_needed,
                            wait_time=total_wait,
                            queue_time=total_wait - wait_time
                        )
                        self.request_history.append(metrics)
                        self.total_requests += 1
                        self.total_wait_time += total_wait
                        return
                    
                    await asyncio.sleep(0.5)
                    waited += 0.5
                
                # Timeout
                raise KeepaRateLimitError(
                    retry_after=int(wait_time),
                    current_usage=self.sliding_window.get_current_usage(),
                    limit=self.config.max_requests_per_minute,
                    details={"timeout_seconds": max_wait, "queue_timeout": True}
                )
                
            except Exception as e:
                self.error_logger.log_rate_limit_status(
                    current_usage=self.sliding_window.get_current_usage(),
                    limit=self.config.max_requests_per_minute,
                    reset_time=datetime.now() + timedelta(seconds=wait_time)
                )
                raise
        
        # Queue full - reject request
        raise KeepaRateLimitError(
            retry_after=int(wait_time),
            current_usage=self.sliding_window.get_current_usage(),
            limit=self.config.max_requests_per_minute,
            details={"queue_full": True}
        )
    
    def _calculate_intelligent_wait_time(self, tokens_needed: int) -> float:
        """Calculate intelligent wait time based on current usage patterns.
        
        Args:
            tokens_needed: Number of tokens needed
            
        Returns:
            Estimated wait time in seconds
        """
        # Token bucket wait time
        token_wait = self.token_bucket.time_until_tokens(tokens_needed)
        
        # Sliding window wait time (estimate based on oldest sub-window)
        current_usage = self.sliding_window.get_current_usage()
        if current_usage + tokens_needed > self.config.max_requests_per_minute:
            # Need to wait for oldest requests to age out
            sliding_wait = self.config.time_window_seconds / self.config.sliding_window_size
        else:
            sliding_wait = 0.0
        
        # Use the maximum of both wait times
        base_wait = max(token_wait, sliding_wait)
        
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.1, 0.5)
        
        # Consider current queue size for additional delay
        queue_factor = 1.0 + (self.request_queue.size() / 100.0)
        
        return base_wait * queue_factor + jitter
    
    def get_rate_limit_status(self) -> RateLimitStatus:
        """Get comprehensive rate limit status for monitoring."""
        current_tokens = self.token_bucket.get_tokens()
        requests_in_window = self.sliding_window.get_current_usage()
        utilization = self.sliding_window.get_utilization()
        
        # Calculate requests per second from recent history
        now = datetime.now()
        recent_requests = [
            r for r in self.request_history 
            if (now - r.timestamp).total_seconds() <= 60
        ]
        requests_per_second = len(recent_requests) / 60.0
        
        return RateLimitStatus(
            current_tokens=current_tokens,
            max_tokens=self.token_bucket.capacity,
            requests_in_window=requests_in_window,
            max_requests=self.config.max_requests_per_minute,
            time_window_seconds=self.config.time_window_seconds,
            utilization_percentage=utilization,
            burst_capacity=self.token_bucket.capacity,
            queue_size=self.request_queue.size(),
            active_requests=self.request_queue.get_active_count(),
            estimated_wait_time=self._calculate_intelligent_wait_time(1),
            last_request_time=recent_requests[-1].timestamp if recent_requests else None,
            requests_per_second=requests_per_second
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "uptime_seconds": uptime,
            "total_requests": self.total_requests,
            "requests_per_second": self.total_requests / uptime if uptime > 0 else 0,
            "average_wait_time": self.total_wait_time / self.total_requests if self.total_requests > 0 else 0,
            "average_queue_time": self.total_queue_time / self.total_requests if self.total_requests > 0 else 0,
            "queue_utilization": (self.request_queue.size() / self.request_queue.max_size) * 100,
            "token_bucket_utilization": (1 - (self.token_bucket.get_tokens() / self.token_bucket.capacity)) * 100,
            "sliding_window_utilization": self.sliding_window.get_utilization()
        }
    
    async def shutdown(self):
        """Gracefully shutdown the rate limiter."""
        self._shutdown_event.set()
        
        if self._queue_processor_task and not self._queue_processor_task.done():
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Rate limiter shutdown complete")


# Legacy compatibility class
class RateLimiter(AdvancedRateLimiter):
    """Legacy compatibility wrapper for the advanced rate limiter."""
    
    def __init__(self, max_requests: int, time_window: int = 60, burst_capacity: Optional[int] = None):
        """Initialize with legacy parameters."""
        config = RateLimitConfig(
            max_requests_per_minute=max_requests,
            burst_capacity=burst_capacity,
            time_window_seconds=time_window
        )
        super().__init__(config)
        
        # Legacy compatibility attributes
        self.max_requests = max_requests
        self.time_window = time_window
        self.burst_capacity = burst_capacity or max_requests * 2
        self.requests = []  # For backward compatibility
    
    def is_allowed(self, tokens_needed: int = 1) -> bool:
        """Legacy method for checking if request is allowed."""
        return (self.token_bucket.consume(tokens_needed) and 
                self.sliding_window.is_allowed(tokens_needed))
    
    def _refill_tokens(self):
        """Legacy method - now handled automatically by token bucket."""
        pass
    
    def _calculate_wait_time(self, tokens_needed: int) -> float:
        """Legacy method for calculating wait time."""
        return self._calculate_intelligent_wait_time(tokens_needed)