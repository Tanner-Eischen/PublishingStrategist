"""Unified HTTP client for standardized request handling across the application.

Provides both async and sync interfaces with consistent error handling,
retry logic, and configuration. Built on top of the RequestManager infrastructure.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

from .request_manager import RequestManager, RequestConfig, LogLevel
from ..exceptions import RequestContext, KDPStrategistError


@dataclass
class HTTPClientConfig:
    """Configuration for HTTP clients."""
    # Timeout settings
    timeout: int = 30
    connect_timeout: int = 10
    read_timeout: int = 20
    
    # Retry settings
    max_retries: int = 3
    base_delay: float = 1.0
    
    # Logging
    log_level: str = "basic"
    
    # User agent
    user_agent: str = "KDP-Strategist/1.0"
    
    def to_request_config(self) -> RequestConfig:
        """Convert to RequestConfig for RequestManager."""
        log_level_map = {
            "none": LogLevel.NONE,
            "basic": LogLevel.BASIC,
            "detailed": LogLevel.DETAILED,
            "full": LogLevel.FULL
        }
        
        return RequestConfig(
            total_timeout=self.timeout,
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            log_level=log_level_map.get(self.log_level, LogLevel.BASIC)
        )


class AsyncHTTPClient:
    """Async HTTP client wrapper around RequestManager."""
    
    def __init__(self, config: Optional[HTTPClientConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or HTTPClientConfig()
        self.logger = logger or logging.getLogger(__name__)
        self._request_manager: Optional[RequestManager] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_request_manager()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def _ensure_request_manager(self):
        """Ensure RequestManager is initialized."""
        if self._request_manager is None:
            request_config = self.config.to_request_config()
            self._request_manager = RequestManager(request_config, self.logger)
            await self._request_manager.__aenter__()
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
                  headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request."""
        await self._ensure_request_manager()
        context = RequestContext(
            endpoint=url.split('/')[-1],
            method="GET",
            params=params or {}
        )
        return await self._request_manager.make_request(
            "GET", url, params=params, headers=headers, context=context
        )
    
    async def post(self, url: str, data: Optional[Any] = None, json: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request."""
        await self._ensure_request_manager()
        context = RequestContext(
            endpoint=url.split('/')[-1],
            method="POST",
            params={}
        )
        request_data = json if json is not None else data
        return await self._request_manager.make_request(
            "POST", url, data=request_data, headers=headers, context=context
        )
    
    async def put(self, url: str, data: Optional[Any] = None, json: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make PUT request."""
        await self._ensure_request_manager()
        context = RequestContext(
            endpoint=url.split('/')[-1],
            method="PUT",
            params={}
        )
        request_data = json if json is not None else data
        return await self._request_manager.make_request(
            "PUT", url, data=request_data, headers=headers, context=context
        )
    
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make DELETE request."""
        await self._ensure_request_manager()
        context = RequestContext(
            endpoint=url.split('/')[-1],
            method="DELETE",
            params={}
        )
        return await self._request_manager.make_request(
            "DELETE", url, headers=headers, context=context
        )
    
    async def close(self):
        """Close the HTTP client and cleanup resources."""
        if self._request_manager:
            await self._request_manager.close()
            self._request_manager = None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get request metrics."""
        if self._request_manager:
            return {
                "total_requests": self._request_manager.metrics.total_requests,
                "successful_requests": self._request_manager.metrics.successful_requests,
                "failed_requests": self._request_manager.metrics.failed_requests,
                "success_rate": self._request_manager.metrics.get_success_rate(),
                "average_response_time": self._request_manager.metrics.get_average_response_time()
            }
        return {}


class SyncHTTPClient:
    """Synchronous HTTP client that wraps AsyncHTTPClient."""
    
    def __init__(self, config: Optional[HTTPClientConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or HTTPClientConfig()
        self.logger = logger or logging.getLogger(__name__)
        self._loop = None
        self._async_client = None
    
    def _ensure_loop(self):
        """Ensure event loop is available."""
        try:
            self._loop = asyncio.get_event_loop()
            if self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        self._ensure_loop()
        
        if self._loop.is_running():
            # If loop is already running, create a new thread
            import concurrent.futures
            import threading
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        else:
            return self._loop.run_until_complete(coro)
    
    async def _get_async_client(self):
        """Get or create async client."""
        if self._async_client is None:
            self._async_client = AsyncHTTPClient(self.config, self.logger)
            await self._async_client.__aenter__()
        return self._async_client
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request."""
        async def _get():
            client = await self._get_async_client()
            return await client.get(url, params=params, headers=headers, **kwargs)
        
        return self._run_async(_get())
    
    def post(self, url: str, data: Optional[Any] = None, json: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request."""
        async def _post():
            client = await self._get_async_client()
            return await client.post(url, data=data, json=json, headers=headers, **kwargs)
        
        return self._run_async(_post())
    
    def put(self, url: str, data: Optional[Any] = None, json: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make PUT request."""
        async def _put():
            client = await self._get_async_client()
            return await client.put(url, data=data, json=json, headers=headers, **kwargs)
        
        return self._run_async(_put())
    
    def delete(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make DELETE request."""
        async def _delete():
            client = await self._get_async_client()
            return await client.delete(url, headers=headers, **kwargs)
        
        return self._run_async(_delete())
    
    def close(self):
        """Close the HTTP client and cleanup resources."""
        if self._async_client:
            async def _close():
                await self._async_client.close()
                self._async_client = None
            
            self._run_async(_close())
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get request metrics."""
        if self._async_client:
            return self._async_client.get_metrics()
        return {}
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class HTTPClientFactory:
    """Factory for creating configured HTTP clients."""
    
    @staticmethod
    def create_async_client(config: Optional[HTTPClientConfig] = None, 
                           logger: Optional[logging.Logger] = None) -> AsyncHTTPClient:
        """Create async HTTP client."""
        return AsyncHTTPClient(config, logger)
    
    @staticmethod
    def create_sync_client(config: Optional[HTTPClientConfig] = None,
                          logger: Optional[logging.Logger] = None) -> SyncHTTPClient:
        """Create sync HTTP client."""
        return SyncHTTPClient(config, logger)
    
    @staticmethod
    def create_client(async_mode: bool = False, config: Optional[HTTPClientConfig] = None,
                     logger: Optional[logging.Logger] = None) -> Union[AsyncHTTPClient, SyncHTTPClient]:
        """Create HTTP client based on mode."""
        if async_mode:
            return HTTPClientFactory.create_async_client(config, logger)
        else:
            return HTTPClientFactory.create_sync_client(config, logger)


# Convenience functions for quick usage
def get_async_client(config: Optional[HTTPClientConfig] = None) -> AsyncHTTPClient:
    """Get async HTTP client with default configuration."""
    return HTTPClientFactory.create_async_client(config)


def get_sync_client(config: Optional[HTTPClientConfig] = None) -> SyncHTTPClient:
    """Get sync HTTP client with default configuration."""
    return HTTPClientFactory.create_sync_client(config)