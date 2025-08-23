"""Centralized request management system for Keepa API client.

This module provides:
- Centralized request manager with retry logic
- Exponential backoff with jitter for failed requests
- Circuit breaker pattern for persistent API failures
- Request timeout handling with configurable values
- Connection pooling and session management
- Request context tracking for debugging and monitoring
- Request/response logging with configurable detail levels
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import json

from ..exceptions import (
    KDPStrategistError, KeepaAPIError, KeepaRateLimitError,
    KeepaAuthenticationError, KeepaTimeoutError, KeepaDataParsingError,
    KeepaServiceUnavailableError, RequestContext
)
from ..exceptions import APIError


class LogLevel(Enum):
    """Request/response logging detail levels."""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"
    FULL = "full"


@dataclass
class RequestConfig:
    """Configuration for request management."""
    # Timeout settings
    total_timeout: int = 30
    connect_timeout: int = 10
    read_timeout: int = 20
    
    # Retry settings
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter_factor: float = 0.1
    
    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3
    
    # Connection pooling settings
    max_connections: int = 100
    max_connections_per_host: int = 10
    connection_timeout: int = 30
    keepalive_timeout: int = 30
    
    # Logging settings
    log_level: LogLevel = LogLevel.BASIC
    log_request_headers: bool = False
    log_response_headers: bool = False
    log_request_body: bool = False
    log_response_body: bool = False
    max_log_body_size: int = 1000


@dataclass
class RequestMetrics:
    """Request performance and reliability metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    circuit_breaker_trips: int = 0
    
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    
    error_counts: Dict[str, int] = field(default_factory=dict)
    status_code_counts: Dict[int, int] = field(default_factory=dict)
    
    def add_request(self, response_time: float, success: bool, status_code: Optional[int] = None, error_type: Optional[str] = None):
        """Add request metrics."""
        self.total_requests += 1
        self.total_response_time += response_time
        
        if response_time < self.min_response_time:
            self.min_response_time = response_time
        if response_time > self.max_response_time:
            self.max_response_time = response_time
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        if status_code:
            self.status_code_counts[status_code] = self.status_code_counts.get(status_code, 0) + 1
    
    def get_success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def get_average_response_time(self) -> float:
        """Get average response time in seconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerStatus:
    """Circuit breaker status and metrics."""
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0
    total_trips: int = 0
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0


class CircuitBreaker:
    """Circuit breaker implementation for request management."""
    
    def __init__(self, config: RequestConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.status = CircuitBreakerStatus()
    
    def can_execute(self) -> bool:
        """Check if request can be executed based on circuit breaker state."""
        now = datetime.now()
        
        if self.status.state == CircuitBreakerState.CLOSED:
            return True
        
        elif self.status.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.status.last_failure_time and 
                now - self.status.last_failure_time >= timedelta(seconds=self.config.recovery_timeout)):
                self.status.state = CircuitBreakerState.HALF_OPEN
                self.status.half_open_calls = 0
                self.logger.info("Circuit breaker transitioning to HALF_OPEN state")
                return True
            return False
        
        elif self.status.state == CircuitBreakerState.HALF_OPEN:
            return self.status.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record successful request."""
        if self.status.state == CircuitBreakerState.HALF_OPEN:
            self.status.half_open_calls += 1
            if self.status.half_open_calls >= self.config.half_open_max_calls:
                self.status.reset()
                self.logger.info("Circuit breaker reset to CLOSED state after successful recovery")
        elif self.status.state == CircuitBreakerState.CLOSED:
            self.status.failure_count = 0
    
    def record_failure(self):
        """Record failed request."""
        self.status.failure_count += 1
        self.status.last_failure_time = datetime.now()
        
        if self.status.state == CircuitBreakerState.CLOSED:
            if self.status.failure_count >= self.config.failure_threshold:
                self.status.state = CircuitBreakerState.OPEN
                self.status.total_trips += 1
                self.logger.warning(f"Circuit breaker OPENED after {self.status.failure_count} failures")
        
        elif self.status.state == CircuitBreakerState.HALF_OPEN:
            self.status.state = CircuitBreakerState.OPEN
            self.status.total_trips += 1
            self.logger.warning("Circuit breaker returned to OPEN state after failure in HALF_OPEN")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status information."""
        return {
            "state": self.status.state.value,
            "failure_count": self.status.failure_count,
            "last_failure_time": self.status.last_failure_time.isoformat() if self.status.last_failure_time else None,
            "half_open_calls": self.status.half_open_calls,
            "total_trips": self.status.total_trips,
            "can_execute": self.can_execute()
        }


class RetryHandler:
    """Handles retry logic with exponential backoff and jitter."""
    
    def __init__(self, config: RequestConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff and jitter."""
        if attempt <= 0:
            return 0.0
        
        # Exponential backoff
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = delay * self.config.jitter_factor * random.random()
        delay += jitter
        
        return delay
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if request should be retried based on attempt count and error type."""
        if attempt >= self.config.max_retries:
            return False
        
        # Define retryable error types
        retryable_errors = (
            KeepaTimeoutError,
            KeepaServiceUnavailableError,
            aiohttp.ClientConnectionError,
            aiohttp.ServerTimeoutError,
            asyncio.TimeoutError
        )
        
        return isinstance(error, retryable_errors)
    
    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        context: RequestContext
    ) -> Any:
        """Execute operation with retry logic."""
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self.calculate_delay(attempt)
                    self.logger.info(f"Retrying request (attempt {attempt + 1}/{self.config.max_retries + 1}) after {delay:.2f}s delay")
                    await asyncio.sleep(delay)
                
                result = await operation()
                
                if attempt > 0:
                    self.logger.info(f"Request succeeded on retry attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_error = e
                
                if not self.should_retry(attempt, e):
                    if attempt >= self.config.max_retries:
                        self.logger.error(f"Request failed after {self.config.max_retries} retries: {e}")
                    else:
                        self.logger.error(f"Request failed with non-retryable error: {e}")
                    break
                
                self.logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
        
        # If we get here, all retries failed
        raise last_error


class RequestLogger:
    """Handles request/response logging with configurable detail levels."""
    
    def __init__(self, config: RequestConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def log_request_start(self, context: RequestContext, url: str, params: Dict[str, Any]):
        """Log request start."""
        if self.config.log_level == LogLevel.NONE:
            return
        
        message = f"Starting request: {context.method} {url}"
        
        if self.config.log_level in [LogLevel.DETAILED, LogLevel.FULL]:
            message += f" | Params: {self._sanitize_params(params)}"
        
        self.logger.info(message)
    
    def log_request_success(
        self,
        context: RequestContext,
        response_time: float,
        status_code: int,
        response_size: int
    ):
        """Log successful request."""
        if self.config.log_level == LogLevel.NONE:
            return
        
        message = f"Request completed: {context.endpoint} | {response_time:.3f}s | {status_code} | {response_size} bytes"
        
        self.logger.info(message)
    
    def log_request_failure(
        self,
        context: RequestContext,
        error: Exception,
        response_time: Optional[float] = None
    ):
        """Log failed request."""
        if self.config.log_level == LogLevel.NONE:
            return
        
        time_info = f" | {response_time:.3f}s" if response_time else ""
        message = f"Request failed: {context.endpoint}{time_info} | {type(error).__name__}: {error}"
        
        self.logger.error(message)
    
    def log_retry_attempt(self, context: RequestContext, attempt: int, delay: float):
        """Log retry attempt."""
        if self.config.log_level in [LogLevel.DETAILED, LogLevel.FULL]:
            self.logger.info(f"Retrying request: {context.endpoint} | Attempt {attempt} | Delay {delay:.2f}s")
    
    def log_circuit_breaker_event(self, event: str, context: RequestContext):
        """Log circuit breaker events."""
        if self.config.log_level in [LogLevel.BASIC, LogLevel.DETAILED, LogLevel.FULL]:
            self.logger.warning(f"Circuit breaker {event}: {context.endpoint}")
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters for logging (remove sensitive data)."""
        sanitized = {}
        sensitive_keys = {'key', 'api_key', 'token', 'password', 'secret'}
        
        for key, value in params.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized


class RequestManager:
    """Centralized request manager with comprehensive error handling and resilience features."""
    
    def __init__(self, config: RequestConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        self.circuit_breaker = CircuitBreaker(config, self.logger)
        self.retry_handler = RetryHandler(config, self.logger)
        self.request_logger = RequestLogger(config, self.logger)
        self.metrics = RequestMetrics()
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        
        # Request tracking
        self.active_requests: Dict[str, RequestContext] = {}
        self._request_counter = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is created and configured."""
        if self.session is None or self.session.closed:
            async with self._session_lock:
                if self.session is None or self.session.closed:
                    # Configure connection pooling
                    connector = aiohttp.TCPConnector(
                        limit=self.config.max_connections,
                        limit_per_host=self.config.max_connections_per_host,
                        ttl_dns_cache=300,  # 5 minutes DNS cache
                        use_dns_cache=True,
                        keepalive_timeout=self.config.keepalive_timeout,
                        enable_cleanup_closed=True
                    )
                    
                    # Configure timeouts
                    timeout = aiohttp.ClientTimeout(
                        total=self.config.total_timeout,
                        connect=self.config.connect_timeout,
                        sock_read=self.config.read_timeout
                    )
                    
                    self.session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout,
                        headers={
                            'User-Agent': 'KDP-Strategist/1.0',
                            'Accept': 'application/json',
                            'Accept-Encoding': 'gzip, deflate'
                        }
                    )
    
    async def make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with comprehensive error handling and resilience features.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            headers: Request headers
            data: Request body data
            context: Request context for tracking and logging
            
        Returns:
            Parsed JSON response data
            
        Raises:
            KeepaAPIError: For API-specific errors
            KeepaTimeoutError: For timeout errors
            KeepaRateLimitError: For rate limit errors
            KeepaServiceUnavailableError: For service unavailable errors
        """
        # Create context if not provided
        if context is None:
            context = RequestContext(
                endpoint=url.split('/')[-1],
                method=method,
                params=params or {}
            )
        
        # Generate request ID for tracking
        self._request_counter += 1
        request_id = f"req_{self._request_counter}_{int(time.time())}"
        context.request_id = request_id
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            error = KeepaServiceUnavailableError(
                message="Circuit breaker is OPEN - service temporarily unavailable",
                context=context
            )
            self.metrics.add_request(0.0, False, error_type="circuit_breaker_open")
            raise error
        
        # Ensure session is available
        await self._ensure_session()
        
        # Track active request
        self.active_requests[request_id] = context
        
        try:
            # Execute request with retry logic
            result = await self.retry_handler.execute_with_retry(
                lambda: self._execute_single_request(method, url, params, headers, data, context),
                context
            )
            
            # Record success
            self.circuit_breaker.record_success()
            return result
            
        except Exception as e:
            # Record failure
            self.circuit_breaker.record_failure()
            raise e
            
        finally:
            # Remove from active requests
            self.active_requests.pop(request_id, None)
    
    async def _execute_single_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]],
        data: Optional[Any],
        context: RequestContext
    ) -> Dict[str, Any]:
        """Execute a single HTTP request without retry logic."""
        start_time = time.time()
        
        # Log request start
        self.request_logger.log_request_start(context, url, params or {})
        
        try:
            # Prepare request arguments
            request_kwargs = {
                'params': params,
                'headers': headers
            }
            
            if data is not None:
                if method.upper() in ['POST', 'PUT', 'PATCH']:
                    if isinstance(data, dict):
                        request_kwargs['json'] = data
                    else:
                        request_kwargs['data'] = data
            
            # Make the request
            async with self.session.request(method, url, **request_kwargs) as response:
                response_time = time.time() - start_time
                response_text = await response.text()
                response_size = len(response_text)
                
                # Handle response based on status code
                if response.status == 200:
                    try:
                        response_data = await response.json()
                        
                        # Log success
                        self.request_logger.log_request_success(
                            context, response_time, response.status, response_size
                        )
                        self.metrics.add_request(response_time, True, response.status)
                        
                        return response_data
                        
                    except json.JSONDecodeError as e:
                        error = KeepaDataParsingError(
                            field="response_json",
                            raw_value=response_text[:200],
                            expected_type="valid JSON",
                            context=context
                        )
                        self.request_logger.log_request_failure(context, error, response_time)
                        self.metrics.add_request(response_time, False, response.status, "json_decode_error")
                        raise error
                
                elif response.status == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', 60))
                    error = KeepaRateLimitError(
                        retry_after=retry_after,
                        current_usage=0,  # Would need to be tracked separately
                        limit=0,  # Would need to be tracked separately
                        context=context
                    )
                    self.request_logger.log_request_failure(context, error, response_time)
                    self.metrics.add_request(response_time, False, response.status, "rate_limit")
                    raise error
                
                elif response.status == 401:
                    # Authentication error
                    error = KeepaAuthenticationError(
                        message="Invalid API key or authentication failed",
                        context=context
                    )
                    self.request_logger.log_request_failure(context, error, response_time)
                    self.metrics.add_request(response_time, False, response.status, "authentication")
                    raise error
                
                elif response.status in [502, 503, 504]:
                    # Service unavailable
                    error = KeepaServiceUnavailableError(
                        message=f"Service unavailable (HTTP {response.status})",
                        context=context
                    )
                    self.request_logger.log_request_failure(context, error, response_time)
                    self.metrics.add_request(response_time, False, response.status, "service_unavailable")
                    raise error
                
                else:
                    # Other HTTP errors
                    error = KeepaAPIError(
                        message=f"HTTP {response.status}: {response_text[:200]}",
                        error_code=f"HTTP_{response.status}",
                        context=context
                    )
                    self.request_logger.log_request_failure(context, error, response_time)
                    self.metrics.add_request(response_time, False, response.status, "http_error")
                    raise error
        
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            error = KeepaTimeoutError(
                timeout_duration=self.config.total_timeout,
                context=context
            )
            self.request_logger.log_request_failure(context, error, response_time)
            self.metrics.add_request(response_time, False, error_type="timeout")
            raise error
        
        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            error = KeepaAPIError(
                message=f"Connection error: {str(e)}",
                error_code="CONNECTION_ERROR",
                context=context
            )
            self.request_logger.log_request_failure(context, error, response_time)
            self.metrics.add_request(response_time, False, error_type="connection_error")
            raise error
        
        except (KeepaAPIError, KeepaTimeoutError, KeepaRateLimitError, 
                KeepaAuthenticationError, KeepaServiceUnavailableError):
            # Re-raise Keepa-specific errors
            raise
        
        except Exception as e:
            response_time = time.time() - start_time
            error = KeepaAPIError(
                message=f"Unexpected request error: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                context=context
            )
            self.request_logger.log_request_failure(context, error, response_time)
            self.metrics.add_request(response_time, False, error_type="unexpected_error")
            raise error
    
    async def make_batch_requests(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Make multiple requests concurrently with proper resource management.
        
        Args:
            requests: List of request dictionaries with keys: method, url, params, headers, data
            max_concurrent: Maximum number of concurrent requests (defaults to config value)
            
        Returns:
            List of response data dictionaries in the same order as requests
        """
        if max_concurrent is None:
            max_concurrent = min(len(requests), self.config.max_connections_per_host)
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def make_single_request(request_data: Dict[str, Any], index: int) -> tuple[int, Dict[str, Any]]:
            async with semaphore:
                try:
                    context = RequestContext(
                        endpoint=request_data.get('url', '').split('/')[-1],
                        method=request_data.get('method', 'GET'),
                        params=request_data.get('params', {})
                    )
                    
                    result = await self.make_request(
                        method=request_data.get('method', 'GET'),
                        url=request_data['url'],
                        params=request_data.get('params'),
                        headers=request_data.get('headers'),
                        data=request_data.get('data'),
                        context=context
                    )
                    return index, result
                    
                except Exception as e:
                    # Return error information instead of raising
                    return index, {
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'success': False
                    }
        
        # Execute all requests concurrently
        tasks = [make_single_request(req, i) for i, req in enumerate(requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sort results by original order and extract response data
        sorted_results = sorted(results, key=lambda x: x[0] if isinstance(x, tuple) else 0)
        return [result[1] for result in sorted_results if isinstance(result, tuple)]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get request performance and reliability metrics."""
        return {
            'total_requests': self.metrics.total_requests,
            'successful_requests': self.metrics.successful_requests,
            'failed_requests': self.metrics.failed_requests,
            'success_rate': self.metrics.get_success_rate(),
            'average_response_time': self.metrics.get_average_response_time(),
            'min_response_time': self.metrics.min_response_time if self.metrics.min_response_time != float('inf') else 0.0,
            'max_response_time': self.metrics.max_response_time,
            'error_counts': dict(self.metrics.error_counts),
            'status_code_counts': dict(self.metrics.status_code_counts),
            'circuit_breaker': self.circuit_breaker.get_status(),
            'active_requests': len(self.active_requests)
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the request manager."""
        return {
            'session_active': self.session is not None and not self.session.closed,
            'circuit_breaker_state': self.circuit_breaker.status.state.value,
            'active_requests': len(self.active_requests),
            'success_rate': self.metrics.get_success_rate(),
            'average_response_time': self.metrics.get_average_response_time(),
            'healthy': (
                self.circuit_breaker.status.state != CircuitBreakerState.OPEN and
                self.metrics.get_success_rate() >= 90.0  # 90% success rate threshold
            )
        }
    
    async def close(self):
        """Close the request manager and clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()
        
        # Wait for any remaining active requests to complete (with timeout)
        if self.active_requests:
            self.logger.info(f"Waiting for {len(self.active_requests)} active requests to complete...")
            await asyncio.sleep(1.0)  # Give requests a moment to complete
        
        self.logger.info("Request manager closed")