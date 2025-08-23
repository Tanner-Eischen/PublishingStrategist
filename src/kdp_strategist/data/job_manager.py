"""Comprehensive job management system with cancellation and cleanup.

This module provides a high-level interface for managing background jobs,
including cancellation, cleanup, and resource management.
"""

import asyncio
import logging
import signal
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import psutil
import os

from .job_queue import JobQueue, JobQueueConfig, JobType, JobPriority, JobStatus
from .job_tracker import JobTracker, JobTrackerConfig, ProgressEventType

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of system resources to monitor."""
    MEMORY = "memory"
    CPU = "cpu"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class ResourceLimits:
    """Resource usage limits."""
    max_memory_mb: int = 1024  # 1GB
    max_cpu_percent: float = 80.0
    max_disk_usage_mb: int = 5120  # 5GB
    max_concurrent_jobs: int = 5
    job_timeout_seconds: int = 3600  # 1 hour


@dataclass
class JobManagerConfig:
    """Configuration for job manager."""
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    enable_resource_monitoring: bool = True
    resource_check_interval: int = 30  # seconds
    enable_graceful_shutdown: bool = True
    shutdown_timeout_seconds: int = 300  # 5 minutes
    enable_job_persistence: bool = True
    cleanup_interval_seconds: int = 600  # 10 minutes
    max_failed_job_retention_hours: int = 24
    enable_auto_scaling: bool = False
    auto_scaling_threshold: float = 0.8  # Scale when 80% capacity used


class JobManager:
    """Comprehensive job management system."""
    
    def __init__(self, config: JobManagerConfig):
        self.config = config
        
        # Initialize job queue and tracker
        queue_config = JobQueueConfig(
            max_concurrent_jobs=config.resource_limits.max_concurrent_jobs,
            job_timeout_seconds=config.resource_limits.job_timeout_seconds,
            persistence_enabled=config.enable_job_persistence
        )
        self.job_queue = JobQueue(queue_config)
        
        tracker_config = JobTrackerConfig()
        self.job_tracker = JobTracker(tracker_config)
        
        # Resource monitoring
        self.current_resource_usage = {
            ResourceType.MEMORY: 0.0,
            ResourceType.CPU: 0.0,
            ResourceType.DISK: 0.0
        }
        
        # Job management
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.job_resources: Dict[str, Dict[ResourceType, float]] = {}
        self.cancelled_jobs: Set[str] = set()
        
        # Background tasks
        self.resource_monitor_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.auto_scaling_task: Optional[asyncio.Task] = None
        
        # Shutdown handling
        self.shutdown_event = asyncio.Event()
        self.shutdown_in_progress = False
        
        # Statistics
        self.stats = {
            "total_jobs_managed": 0,
            "jobs_cancelled_by_user": 0,
            "jobs_cancelled_by_resource_limit": 0,
            "jobs_cancelled_by_timeout": 0,
            "resource_limit_violations": 0,
            "graceful_shutdowns": 0
        }
        
        # Setup signal handlers for graceful shutdown
        if config.enable_graceful_shutdown:
            self._setup_signal_handlers()
    
    async def start(self) -> None:
        """Start the job manager."""
        logger.info("Starting job manager")
        
        # Start job queue and tracker
        await self.job_queue.start()
        await self.job_tracker.start()
        
        # Connect job queue events to tracker
        self._connect_queue_to_tracker()
        
        # Start background tasks
        if self.config.enable_resource_monitoring:
            self.resource_monitor_task = asyncio.create_task(self._resource_monitor_worker())
        
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        if self.config.enable_auto_scaling:
            self.auto_scaling_task = asyncio.create_task(self._auto_scaling_worker())
        
        logger.info("Job manager started")
    
    async def stop(self) -> None:
        """Stop the job manager gracefully."""
        logger.info("Stopping job manager")
        
        self.shutdown_in_progress = True
        self.shutdown_event.set()
        
        # Cancel all background tasks
        tasks_to_cancel = [
            self.resource_monitor_task,
            self.cleanup_task,
            self.auto_scaling_task
        ]
        
        for task in tasks_to_cancel:
            if task:
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*[task for task in tasks_to_cancel if task], return_exceptions=True)
        
        # Stop job queue and tracker
        await self.job_queue.stop()
        await self.job_tracker.stop()
        
        self.stats["graceful_shutdowns"] += 1
        logger.info("Job manager stopped")
    
    async def submit_job(self, 
                        job_type: JobType,
                        function: Callable,
                        *args,
                        priority: JobPriority = JobPriority.NORMAL,
                        max_retries: int = 3,
                        timeout_seconds: Optional[int] = None,
                        expected_resources: Optional[Dict[ResourceType, float]] = None,
                        dependencies: Optional[List[str]] = None,
                        **kwargs) -> str:
        """Submit a job with resource management."""
        
        # Check resource availability
        if expected_resources and not await self._check_resource_availability(expected_resources):
            raise RuntimeError("Insufficient resources to run job")
        
        # Submit to job queue
        job_id = await self.job_queue.submit_job(
            job_type,
            function,
            *args,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            dependencies=dependencies,
            **kwargs
        )
        
        # Track job
        self.job_tracker.track_job(
            job_id=job_id,
            job_type=job_type.value,
            status="pending",
            priority=priority.value,
            dependencies=dependencies
        )
        
        # Record expected resources
        if expected_resources:
            self.job_resources[job_id] = expected_resources
        
        self.active_jobs[job_id] = {
            "job_type": job_type,
            "submitted_at": datetime.now(),
            "expected_resources": expected_resources or {}
        }
        
        self.stats["total_jobs_managed"] += 1
        
        logger.info(f"Submitted job {job_id} ({job_type.value})")
        return job_id
    
    async def cancel_job(self, job_id: str, reason: str = "User requested") -> bool:
        """Cancel a job with cleanup."""
        if job_id in self.cancelled_jobs:
            return False  # Already cancelled
        
        # Cancel in job queue
        success = await self.job_queue.cancel_job(job_id, reason)
        
        if success:
            self.cancelled_jobs.add(job_id)
            
            # Update tracker
            self.job_tracker.update_job_status(job_id, "cancelled", f"Cancelled: {reason}")
            
            # Clean up resources
            await self._cleanup_job_resources(job_id)
            
            # Update statistics
            if "user" in reason.lower():
                self.stats["jobs_cancelled_by_user"] += 1
            elif "resource" in reason.lower():
                self.stats["jobs_cancelled_by_resource_limit"] += 1
            elif "timeout" in reason.lower():
                self.stats["jobs_cancelled_by_timeout"] += 1
            
            logger.info(f"Cancelled job {job_id}: {reason}")
        
        return success
    
    async def cancel_all_jobs(self, reason: str = "System shutdown") -> int:
        """Cancel all active jobs."""
        active_job_ids = list(self.active_jobs.keys())
        cancelled_count = 0
        
        for job_id in active_job_ids:
            if await self.cancel_job(job_id, reason):
                cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count} jobs: {reason}")
        return cancelled_count
    
    async def cancel_jobs_by_type(self, job_type: JobType, reason: str = "Type-specific cancellation") -> int:
        """Cancel all jobs of a specific type."""
        jobs_to_cancel = [
            job_id for job_id, job_info in self.active_jobs.items()
            if job_info["job_type"] == job_type
        ]
        
        cancelled_count = 0
        for job_id in jobs_to_cancel:
            if await self.cancel_job(job_id, reason):
                cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count} {job_type.value} jobs: {reason}")
        return cancelled_count
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive job status."""
        # Get status from queue
        queue_status = await self.job_queue.get_job_status(job_id)
        if not queue_status:
            return None
        
        # Get tracking info
        tracking_info = self.job_tracker.get_job_info(job_id)
        
        # Combine information
        status = queue_status.copy()
        if tracking_info:
            status.update({
                "tracking_info": tracking_info.to_dict(),
                "recent_events": [event.to_dict() for event in tracking_info.get_recent_events()]
            })
        
        # Add resource information
        if job_id in self.job_resources:
            status["expected_resources"] = self.job_resources[job_id]
        
        return status
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        queue_status = await self.job_queue.get_queue_status()
        performance_analytics = self.job_tracker.get_performance_analytics()
        
        return {
            "queue_status": queue_status,
            "performance_analytics": performance_analytics,
            "resource_usage": self.current_resource_usage,
            "resource_limits": {
                "max_memory_mb": self.config.resource_limits.max_memory_mb,
                "max_cpu_percent": self.config.resource_limits.max_cpu_percent,
                "max_concurrent_jobs": self.config.resource_limits.max_concurrent_jobs
            },
            "active_jobs_count": len(self.active_jobs),
            "cancelled_jobs_count": len(self.cancelled_jobs),
            "manager_stats": self.stats,
            "shutdown_in_progress": self.shutdown_in_progress
        }
    
    async def cleanup_failed_jobs(self, older_than_hours: int = 24) -> int:
        """Clean up failed jobs older than specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        jobs_to_cleanup = []
        for job_id, job_info in self.active_jobs.items():
            if job_info["submitted_at"] < cutoff_time:
                # Check if job is failed or completed
                status = await self.get_job_status(job_id)
                if status and status.get("status") in ["failed", "completed", "cancelled"]:
                    jobs_to_cleanup.append(job_id)
        
        # Clean up jobs
        for job_id in jobs_to_cleanup:
            await self._cleanup_job_resources(job_id)
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            if job_id in self.job_resources:
                del self.job_resources[job_id]
            self.cancelled_jobs.discard(job_id)
        
        logger.info(f"Cleaned up {len(jobs_to_cleanup)} old jobs")
        return len(jobs_to_cleanup)
    
    async def force_cleanup_resources(self) -> None:
        """Force cleanup of all job resources."""
        logger.info("Forcing cleanup of all job resources")
        
        # Cancel all active jobs
        await self.cancel_all_jobs("Force cleanup")
        
        # Clean up resource tracking
        self.active_jobs.clear()
        self.job_resources.clear()
        self.cancelled_jobs.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        logger.info("Force cleanup completed")
    
    def _connect_queue_to_tracker(self) -> None:
        """Connect job queue events to job tracker."""
        
        def on_job_progress(job_id: str, progress):
            """Handle job progress updates."""
            self.job_tracker.update_job_progress(
                job_id=job_id,
                current_step=progress.current_step,
                total_steps=progress.total_steps,
                message=progress.message,
                **progress.details
            )
        
        def on_job_completion(job_id: str, result):
            """Handle job completion."""
            if result.success:
                self.job_tracker.update_job_status(job_id, "completed", "Job completed successfully")
            else:
                self.job_tracker.update_job_status(
                    job_id, "failed", "Job failed", 
                    error_message=result.error_message
                )
            
            # Clean up resources
            asyncio.create_task(self._cleanup_job_resources(job_id))
        
        # Add callbacks to job queue
        self.job_queue.add_progress_callback(on_job_progress)
        self.job_queue.add_completion_callback(on_job_completion)
    
    async def _check_resource_availability(self, expected_resources: Dict[ResourceType, float]) -> bool:
        """Check if resources are available for a job."""
        current_usage = await self._get_current_resource_usage()
        
        for resource_type, required_amount in expected_resources.items():
            current_amount = current_usage.get(resource_type, 0.0)
            
            if resource_type == ResourceType.MEMORY:
                if current_amount + required_amount > self.config.resource_limits.max_memory_mb:
                    return False
            elif resource_type == ResourceType.CPU:
                if current_amount + required_amount > self.config.resource_limits.max_cpu_percent:
                    return False
            elif resource_type == ResourceType.DISK:
                if current_amount + required_amount > self.config.resource_limits.max_disk_usage_mb:
                    return False
        
        return True
    
    async def _get_current_resource_usage(self) -> Dict[ResourceType, float]:
        """Get current system resource usage."""
        try:
            # Memory usage
            memory_info = psutil.virtual_memory()
            memory_usage_mb = (memory_info.total - memory_info.available) / (1024 * 1024)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Disk usage (for current directory)
            disk_usage = psutil.disk_usage('.')
            disk_usage_mb = (disk_usage.total - disk_usage.free) / (1024 * 1024)
            
            return {
                ResourceType.MEMORY: memory_usage_mb,
                ResourceType.CPU: cpu_percent,
                ResourceType.DISK: disk_usage_mb
            }
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            return {resource_type: 0.0 for resource_type in ResourceType}
    
    async def _cleanup_job_resources(self, job_id: str) -> None:
        """Clean up resources for a specific job."""
        # Remove from active jobs
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
        
        # Remove resource tracking
        if job_id in self.job_resources:
            del self.job_resources[job_id]
        
        # Additional cleanup can be added here (e.g., temporary files, connections)
    
    async def _resource_monitor_worker(self) -> None:
        """Background worker for resource monitoring."""
        while not self.shutdown_event.is_set():
            try:
                # Update current resource usage
                self.current_resource_usage = await self._get_current_resource_usage()
                
                # Check for resource limit violations
                await self._check_resource_limits()
                
                await asyncio.sleep(self.config.resource_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
                await asyncio.sleep(self.config.resource_check_interval)
    
    async def _check_resource_limits(self) -> None:
        """Check and enforce resource limits."""
        violations = []
        
        # Check memory limit
        if self.current_resource_usage[ResourceType.MEMORY] > self.config.resource_limits.max_memory_mb:
            violations.append(("memory", self.current_resource_usage[ResourceType.MEMORY]))
        
        # Check CPU limit
        if self.current_resource_usage[ResourceType.CPU] > self.config.resource_limits.max_cpu_percent:
            violations.append(("cpu", self.current_resource_usage[ResourceType.CPU]))
        
        if violations:
            self.stats["resource_limit_violations"] += len(violations)
            
            # Cancel lowest priority jobs to free resources
            await self._handle_resource_violations(violations)
    
    async def _handle_resource_violations(self, violations: List[tuple]) -> None:
        """Handle resource limit violations by cancelling jobs."""
        logger.warning(f"Resource limit violations detected: {violations}")
        
        # Get active jobs sorted by priority (lowest first)
        active_jobs = list(self.active_jobs.items())
        queue_statuses = []
        
        for job_id, _ in active_jobs:
            status = await self.job_queue.get_job_status(job_id)
            if status:
                queue_statuses.append((job_id, status))
        
        # Sort by priority (lower number = higher priority, so cancel higher numbers first)
        queue_statuses.sort(key=lambda x: x[1].get("priority", 2), reverse=True)
        
        # Cancel jobs until resource usage is acceptable
        cancelled_count = 0
        for job_id, status in queue_statuses:
            if cancelled_count >= 3:  # Don't cancel too many at once
                break
            
            await self.cancel_job(job_id, f"Resource limit violation: {violations}")
            cancelled_count += 1
            
            # Check if violations are resolved
            await asyncio.sleep(1)  # Give time for cleanup
            current_usage = await self._get_current_resource_usage()
            
            violations_resolved = True
            if current_usage[ResourceType.MEMORY] > self.config.resource_limits.max_memory_mb:
                violations_resolved = False
            if current_usage[ResourceType.CPU] > self.config.resource_limits.max_cpu_percent:
                violations_resolved = False
            
            if violations_resolved:
                break
        
        logger.info(f"Cancelled {cancelled_count} jobs due to resource violations")
    
    async def _cleanup_worker(self) -> None:
        """Background worker for periodic cleanup."""
        while not self.shutdown_event.is_set():
            try:
                # Clean up old failed jobs
                await self.cleanup_failed_jobs(self.config.max_failed_job_retention_hours)
                
                await asyncio.sleep(self.config.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                await asyncio.sleep(self.config.cleanup_interval_seconds)
    
    async def _auto_scaling_worker(self) -> None:
        """Background worker for auto-scaling (if enabled)."""
        while not self.shutdown_event.is_set():
            try:
                # Check if scaling is needed
                queue_status = await self.job_queue.get_queue_status()
                
                pending_jobs = queue_status.get("pending_queue_size", 0)
                running_jobs = queue_status.get("running_jobs", 0)
                max_concurrent = self.config.resource_limits.max_concurrent_jobs
                
                utilization = running_jobs / max_concurrent
                
                if utilization > self.config.auto_scaling_threshold and pending_jobs > 0:
                    # Consider scaling up (this is a placeholder for actual scaling logic)
                    logger.info(f"High utilization detected: {utilization:.2f}, {pending_jobs} pending jobs")
                
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-scaling worker: {e}")
                await asyncio.sleep(60)
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self._graceful_shutdown())
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown."""
        if self.shutdown_in_progress:
            return
        
        logger.info("Starting graceful shutdown")
        self.shutdown_in_progress = True
        
        # Cancel all jobs with grace period
        await self.cancel_all_jobs("System shutdown")
        
        # Wait for jobs to complete or timeout
        timeout = self.config.shutdown_timeout_seconds
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            queue_status = await self.job_queue.get_queue_status()
            if queue_status.get("running_jobs", 0) == 0:
                break
            await asyncio.sleep(1)
        
        # Force stop if timeout exceeded
        if (datetime.now() - start_time).total_seconds() >= timeout:
            logger.warning("Graceful shutdown timeout exceeded, forcing stop")
            await self.force_cleanup_resources()
        
        # Stop the manager
        await self.stop()


def create_job_manager(config: Optional[JobManagerConfig] = None) -> JobManager:
    """Create a job manager with default or provided configuration."""
    if config is None:
        config = JobManagerConfig()
    return JobManager(config)