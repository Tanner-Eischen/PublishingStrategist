"""Health check endpoints and monitoring utilities for KDP Strategist.

This module provides comprehensive health checks for various system components
including external APIs, cache, database, and overall system health.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

import aiohttp
import psutil

from .exceptions import KDPStrategistError, ExternalServiceError
from .logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.now)
    uptime_seconds: float = 0.0
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": self.uptime_seconds,
            "version": self.version,
            "checks": [check.to_dict() for check in self.checks]
        }


class HealthChecker:
    """Centralized health checking system."""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_check_time: Optional[datetime] = None
        self.cached_results: Dict[str, HealthCheckResult] = {}
        self.cache_ttl = 30  # Cache results for 30 seconds
    
    async def check_system_health(self, include_detailed: bool = False) -> SystemHealth:
        """Perform comprehensive system health check."""
        start_time = time.time()
        
        # Basic health checks (always performed)
        basic_checks = [
            await self.check_application_health(),
            await self.check_memory_usage(),
            await self.check_disk_space()
        ]
        
        # Detailed checks (optional, for monitoring endpoints)
        detailed_checks = []
        if include_detailed:
            detailed_checks = [
                await self.check_google_trends_api(),
                await self.check_keepa_api(),
                await self.check_cache_system(),
                await self.check_database_connection()
            ]
        
        all_checks = basic_checks + detailed_checks
        
        # Determine overall status
        overall_status = self._determine_overall_status(all_checks)
        
        duration_ms = (time.time() - start_time) * 1000
        
        system_health = SystemHealth(
            status=overall_status,
            checks=all_checks,
            uptime_seconds=time.time() - self.start_time
        )
        
        self.last_check_time = datetime.now()
        
        logger.info(f"System health check completed in {duration_ms:.2f}ms", extra={
            "status": overall_status.value,
            "checks_count": len(all_checks),
            "duration_ms": duration_ms
        })
        
        return system_health
    
    async def check_application_health(self) -> HealthCheckResult:
        """Check basic application health."""
        start_time = time.time()
        
        try:
            # Basic application checks
            uptime = time.time() - self.start_time
            
            status = HealthStatus.HEALTHY
            message = "Application is running normally"
            details = {
                "uptime_seconds": uptime,
                "uptime_human": self._format_uptime(uptime)
            }
            
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Application health check failed: {e}"
            details = {"error": str(e)}
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            name="application",
            status=status,
            message=message,
            duration_ms=duration_ms,
            details=details
        )
    
    async def check_memory_usage(self) -> HealthCheckResult:
        """Check system memory usage."""
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent < 80:
                status = HealthStatus.HEALTHY
                message = f"Memory usage is normal ({memory_percent:.1f}%)"
            elif memory_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"Memory usage is high ({memory_percent:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage is critical ({memory_percent:.1f}%)"
            
            details = {
                "memory_percent": memory_percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_total_gb": memory.total / (1024**3)
            }
            
        except Exception as e:
            status = HealthStatus.UNKNOWN
            message = f"Memory check failed: {e}"
            details = {"error": str(e)}
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            name="memory",
            status=status,
            message=message,
            duration_ms=duration_ms,
            details=details
        )
    
    async def check_disk_space(self) -> HealthCheckResult:
        """Check available disk space."""
        start_time = time.time()
        
        try:
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            free_gb = disk.free / (1024**3)
            
            if disk_percent < 80:
                status = HealthStatus.HEALTHY
                message = f"Disk space is sufficient ({free_gb:.1f}GB free)"
            elif disk_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"Disk space is low ({free_gb:.1f}GB free)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Disk space is critical ({free_gb:.1f}GB free)"
            
            details = {
                "disk_percent_used": disk_percent,
                "disk_free_gb": free_gb,
                "disk_total_gb": disk.total / (1024**3)
            }
            
        except Exception as e:
            status = HealthStatus.UNKNOWN
            message = f"Disk check failed: {e}"
            details = {"error": str(e)}
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            name="disk",
            status=status,
            message=message,
            duration_ms=duration_ms,
            details=details
        )
    
    async def check_google_trends_api(self) -> HealthCheckResult:
        """Check Google Trends API availability."""
        start_time = time.time()
        
        try:
            # Simple connectivity check to Google
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get('https://trends.google.com') as response:
                    if response.status == 200:
                        status = HealthStatus.HEALTHY
                        message = "Google Trends API is accessible"
                        details = {"response_code": response.status}
                    else:
                        status = HealthStatus.DEGRADED
                        message = f"Google Trends API returned status {response.status}"
                        details = {"response_code": response.status}
        
        except asyncio.TimeoutError:
            status = HealthStatus.UNHEALTHY
            message = "Google Trends API connection timeout"
            details = {"error": "timeout"}
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Google Trends API check failed: {e}"
            details = {"error": str(e)}
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            name="google_trends",
            status=status,
            message=message,
            duration_ms=duration_ms,
            details=details
        )
    
    async def check_keepa_api(self) -> HealthCheckResult:
        """Check Keepa API availability."""
        start_time = time.time()
        
        try:
            from config.settings import Settings
            settings = Settings.from_env()
            
            if not settings.api.keepa_api_key:
                status = HealthStatus.DEGRADED
                message = "Keepa API key not configured"
                details = {"configured": False}
            else:
                # Simple connectivity check to Keepa
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    headers = {"X-API-KEY": settings.api.keepa_api_key}
                    async with session.get('https://api.keepa.com/token', headers=headers) as response:
                        if response.status == 200:
                            status = HealthStatus.HEALTHY
                            message = "Keepa API is accessible"
                            details = {"configured": True, "response_code": response.status}
                        else:
                            status = HealthStatus.DEGRADED
                            message = f"Keepa API returned status {response.status}"
                            details = {"configured": True, "response_code": response.status}
        
        except asyncio.TimeoutError:
            status = HealthStatus.UNHEALTHY
            message = "Keepa API connection timeout"
            details = {"error": "timeout"}
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Keepa API check failed: {e}"
            details = {"error": str(e)}
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            name="keepa_api",
            status=status,
            message=message,
            duration_ms=duration_ms,
            details=details
        )
    
    async def check_cache_system(self) -> HealthCheckResult:
        """Check cache system health."""
        start_time = time.time()
        
        try:
            from config.settings import Settings
            settings = Settings.from_env()
            
            cache_type = settings.cache.cache_type
            
            if cache_type == "file":
                # Check if cache directory is accessible
                cache_dir = settings.cache.cache_dir
                if cache_dir.exists() and cache_dir.is_dir():
                    status = HealthStatus.HEALTHY
                    message = f"File cache is accessible at {cache_dir}"
                    details = {"cache_type": "file", "cache_dir": str(cache_dir)}
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"File cache directory not accessible: {cache_dir}"
                    details = {"cache_type": "file", "cache_dir": str(cache_dir)}
            
            elif cache_type == "redis":
                # TODO: Implement Redis connectivity check when Redis client is available
                status = HealthStatus.UNKNOWN
                message = "Redis cache check not implemented"
                details = {"cache_type": "redis"}
            
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory cache is available"
                details = {"cache_type": "memory"}
        
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Cache system check failed: {e}"
            details = {"error": str(e)}
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            name="cache",
            status=status,
            message=message,
            duration_ms=duration_ms,
            details=details
        )
    
    async def check_database_connection(self) -> HealthCheckResult:
        """Check database connection health."""
        start_time = time.time()
        
        try:
            # TODO: Implement database connectivity check when database client is available
            status = HealthStatus.UNKNOWN
            message = "Database check not implemented"
            details = {"database_type": "sqlite"}
        
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Database check failed: {e}"
            details = {"error": str(e)}
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            name="database",
            status=status,
            message=message,
            duration_ms=duration_ms,
            details=details
        )
    
    def _determine_overall_status(self, checks: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall system status based on individual checks."""
        if not checks:
            return HealthStatus.UNKNOWN
        
        # Count status types
        status_counts = {}
        for check in checks:
            status_counts[check.status] = status_counts.get(check.status, 0) + 1
        
        # Determine overall status
        if status_counts.get(HealthStatus.UNHEALTHY, 0) > 0:
            return HealthStatus.UNHEALTHY
        elif status_counts.get(HealthStatus.DEGRADED, 0) > 0:
            return HealthStatus.DEGRADED
        elif status_counts.get(HealthStatus.HEALTHY, 0) > 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format."""
        uptime = timedelta(seconds=int(uptime_seconds))
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    
    if _health_checker is None:
        _health_checker = HealthChecker()
    
    return _health_checker