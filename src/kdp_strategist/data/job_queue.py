"""Async task queue system for long-running analysis operations.

This module implements a comprehensive job queue system with status tracking,
progress reporting, cancellation, and retry logic with exponential backoff.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import pickle
from pathlib import Path
import traceback
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class JobType(Enum):
    """Types of background jobs."""
    NICHE_DISCOVERY = "niche_discovery"
    TREND_ANALYSIS = "trend_analysis"
    COMPETITION_ANALYSIS = "competition_analysis"
    KEYWORD_EXPANSION = "keyword_expansion"
    PROFITABILITY_SCORING = "profitability_scoring"
    CACHE_WARMING = "cache_warming"
    DATA_EXPORT = "data_export"
    BATCH_PROCESSING = "batch_processing"


@dataclass
class JobProgress:
    """Represents job progress information."""
    current_step: int = 0
    total_steps: int = 0
    percentage: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, current: int, total: int, message: str = "", **details):
        """Update progress information."""
        self.current_step = current
        self.total_steps = total
        self.percentage = (current / total * 100) if total > 0 else 0.0
        self.message = message
        self.details.update(details)


@dataclass
class JobResult:
    """Represents job execution result."""
    success: bool
    data: Any = None
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    execution_time_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Job:
    """Represents a background job."""
    job_id: str
    job_type: JobType
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_seconds: Optional[int] = None
    
    # Status tracking
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress and results
    progress: JobProgress = field(default_factory=JobProgress)
    result: Optional[JobResult] = None
    
    # Retry tracking
    retry_count: int = 0
    last_error: Optional[str] = None
    
    # Cancellation
    cancelled: bool = False
    cancel_reason: Optional[str] = None
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    
    def can_run(self, completed_jobs: set) -> bool:
        """Check if job can run based on dependencies."""
        return all(dep_id in completed_jobs for dep_id in self.dependencies)
    
    def is_expired(self) -> bool:
        """Check if job has expired."""
        if self.timeout_seconds is None:
            return False
        
        if self.started_at is None:
            # Check if job has been pending too long
            return (datetime.now() - self.created_at).total_seconds() > self.timeout_seconds * 2
        
        return (datetime.now() - self.started_at).total_seconds() > self.timeout_seconds
    
    def should_retry(self) -> bool:
        """Check if job should be retried."""
        return (self.status == JobStatus.FAILED and 
                self.retry_count < self.max_retries and 
                not self.cancelled)
    
    def calculate_retry_delay(self) -> float:
        """Calculate delay before next retry using exponential backoff."""
        return self.retry_delay * (2 ** self.retry_count)


@dataclass
class JobQueueConfig:
    """Configuration for job queue system."""
    max_concurrent_jobs: int = 5
    max_queue_size: int = 1000
    job_timeout_seconds: int = 3600  # 1 hour default
    cleanup_interval_seconds: int = 300  # 5 minutes
    persistence_enabled: bool = True
    persistence_path: Path = Path("cache/job_queue.db")
    progress_update_interval: float = 1.0
    enable_job_dependencies: bool = True
    enable_job_metrics: bool = True


class JobQueue:
    """Async task queue for background job processing."""
    
    def __init__(self, config: JobQueueConfig):
        self.config = config
        self.jobs: Dict[str, Job] = {}
        self.pending_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=config.max_queue_size)
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.completed_jobs: set = set()
        
        # Worker management
        self.workers: List[asyncio.Task] = []
        self.worker_semaphore = asyncio.Semaphore(config.max_concurrent_jobs)
        self.shutdown_event = asyncio.Event()
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None
        
        # Thread pool for CPU-intensive tasks
        self.thread_pool = ThreadPoolExecutor(max_workers=config.max_concurrent_jobs)
        
        # Statistics
        self.stats = {
            "jobs_submitted": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "jobs_cancelled": 0,
            "jobs_retried": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }
        
        # Job metrics
        self.job_metrics: Dict[JobType, Dict[str, Any]] = {}
        
        # Progress callbacks
        self.progress_callbacks: List[Callable[[str, JobProgress], None]] = []
        self.completion_callbacks: List[Callable[[str, JobResult], None]] = []
    
    async def start(self) -> None:
        """Start the job queue system."""
        logger.info("Starting job queue system")
        
        # Load persisted jobs
        if self.config.persistence_enabled:
            await self._load_jobs()
        
        # Start worker tasks
        for i in range(self.config.max_concurrent_jobs):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        
        # Start background tasks
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        if self.config.enable_job_metrics:
            self.metrics_task = asyncio.create_task(self._metrics_worker())
        
        logger.info(f"Started {len(self.workers)} job workers")
    
    async def stop(self) -> None:
        """Stop the job queue system gracefully."""
        logger.info("Stopping job queue system")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Cancel all running jobs
        for job_id in list(self.running_jobs.keys()):
            await self.cancel_job(job_id, "System shutdown")
        
        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Stop background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.metrics_task:
            self.metrics_task.cancel()
        
        # Persist jobs
        if self.config.persistence_enabled:
            await self._save_jobs()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Job queue system stopped")
    
    async def submit_job(self, 
                        job_type: JobType,
                        function: Callable,
                        *args,
                        priority: JobPriority = JobPriority.NORMAL,
                        max_retries: int = 3,
                        retry_delay: float = 1.0,
                        timeout_seconds: Optional[int] = None,
                        dependencies: Optional[List[str]] = None,
                        **kwargs) -> str:
        """Submit a job to the queue."""
        
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            job_type=job_type,
            function=function,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout_seconds=timeout_seconds or self.config.job_timeout_seconds,
            dependencies=dependencies or []
        )
        
        self.jobs[job_id] = job
        
        # Add to queue with priority (lower number = higher priority)
        priority_value = (4 - priority.value, time.time())  # Invert priority and add timestamp for FIFO within same priority
        
        try:
            await self.pending_queue.put((priority_value, job_id))
            self.stats["jobs_submitted"] += 1
            logger.info(f"Submitted job {job_id} ({job_type.value}) with priority {priority.value}")
            return job_id
        except asyncio.QueueFull:
            del self.jobs[job_id]
            raise RuntimeError("Job queue is full")
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and progress."""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        return {
            "job_id": job_id,
            "job_type": job.job_type.value,
            "status": job.status.value,
            "priority": job.priority.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "progress": {
                "current_step": job.progress.current_step,
                "total_steps": job.progress.total_steps,
                "percentage": job.progress.percentage,
                "message": job.progress.message,
                "details": job.progress.details
            },
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "last_error": job.last_error,
            "cancelled": job.cancelled,
            "cancel_reason": job.cancel_reason,
            "result": {
                "success": job.result.success,
                "error_message": job.result.error_message,
                "execution_time_seconds": job.result.execution_time_seconds,
                "metadata": job.result.metadata
            } if job.result else None
        }
    
    async def cancel_job(self, job_id: str, reason: str = "User requested") -> bool:
        """Cancel a job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        job.cancelled = True
        job.cancel_reason = reason
        
        # Cancel running task if exists
        if job_id in self.running_jobs:
            task = self.running_jobs[job_id]
            task.cancel()
            
            # Wait a bit for graceful cancellation
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        # Update status
        if job.status in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRYING]:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            self.stats["jobs_cancelled"] += 1
        
        logger.info(f"Cancelled job {job_id}: {reason}")
        return True
    
    async def retry_job(self, job_id: str) -> bool:
        """Manually retry a failed job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status != JobStatus.FAILED or job.cancelled:
            return False
        
        # Reset job for retry
        job.status = JobStatus.PENDING
        job.started_at = None
        job.completed_at = None
        job.result = None
        job.retry_count += 1
        
        # Re-add to queue
        priority_value = (4 - job.priority.value, time.time())
        await self.pending_queue.put((priority_value, job_id))
        
        logger.info(f"Manually retrying job {job_id} (attempt {job.retry_count + 1})")
        return True
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status."""
        status_counts = {}
        for status in JobStatus:
            status_counts[status.value] = sum(1 for job in self.jobs.values() if job.status == status)
        
        return {
            "total_jobs": len(self.jobs),
            "pending_queue_size": self.pending_queue.qsize(),
            "running_jobs": len(self.running_jobs),
            "completed_jobs": len(self.completed_jobs),
            "status_breakdown": status_counts,
            "statistics": self.stats,
            "worker_count": len(self.workers),
            "max_concurrent_jobs": self.config.max_concurrent_jobs
        }
    
    async def get_job_history(self, limit: int = 100, job_type: Optional[JobType] = None) -> List[Dict[str, Any]]:
        """Get job history."""
        jobs = list(self.jobs.values())
        
        # Filter by job type if specified
        if job_type:
            jobs = [job for job in jobs if job.job_type == job_type]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Limit results
        jobs = jobs[:limit]
        
        return [await self.get_job_status(job.job_id) for job in jobs]
    
    def add_progress_callback(self, callback: Callable[[str, JobProgress], None]) -> None:
        """Add a callback for job progress updates."""
        self.progress_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable[[str, JobResult], None]) -> None:
        """Add a callback for job completion."""
        self.completion_callbacks.append(callback)
    
    async def _worker(self, worker_name: str) -> None:
        """Worker coroutine that processes jobs from the queue."""
        logger.info(f"Started worker: {worker_name}")
        
        while not self.shutdown_event.is_set():
            try:
                # Get next job from queue with timeout
                try:
                    priority_value, job_id = await asyncio.wait_for(
                        self.pending_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                if job_id not in self.jobs:
                    continue
                
                job = self.jobs[job_id]
                
                # Check if job was cancelled
                if job.cancelled:
                    continue
                
                # Check dependencies
                if not job.can_run(self.completed_jobs):
                    # Re-queue job for later
                    await self.pending_queue.put((priority_value, job_id))
                    await asyncio.sleep(1.0)  # Wait before retrying
                    continue
                
                # Acquire semaphore for concurrent job limit
                async with self.worker_semaphore:
                    await self._execute_job(job, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker {worker_name}: {e}")
                await asyncio.sleep(1.0)
        
        logger.info(f"Stopped worker: {worker_name}")
    
    async def _execute_job(self, job: Job, worker_name: str) -> None:
        """Execute a single job."""
        job_id = job.job_id
        
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            
            logger.info(f"Worker {worker_name} executing job {job_id} ({job.job_type.value})")
            
            # Create task for job execution
            task = asyncio.create_task(self._run_job_function(job))
            self.running_jobs[job_id] = task
            
            # Execute with timeout
            start_time = time.time()
            
            try:
                if job.timeout_seconds:
                    result = await asyncio.wait_for(task, timeout=job.timeout_seconds)
                else:
                    result = await task
                
                execution_time = time.time() - start_time
                
                # Job completed successfully
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.result = JobResult(
                    success=True,
                    data=result,
                    execution_time_seconds=execution_time
                )
                
                self.completed_jobs.add(job_id)
                self.stats["jobs_completed"] += 1
                self.stats["total_execution_time"] += execution_time
                self.stats["average_execution_time"] = self.stats["total_execution_time"] / self.stats["jobs_completed"]
                
                logger.info(f"Job {job_id} completed successfully in {execution_time:.2f}s")
                
                # Notify completion callbacks
                for callback in self.completion_callbacks:
                    try:
                        callback(job_id, job.result)
                    except Exception as e:
                        logger.error(f"Error in completion callback: {e}")
                
            except asyncio.TimeoutError:
                job.last_error = f"Job timed out after {job.timeout_seconds} seconds"
                await self._handle_job_failure(job, job.last_error)
                
            except asyncio.CancelledError:
                if job.cancelled:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = datetime.now()
                    logger.info(f"Job {job_id} was cancelled")
                else:
                    # Unexpected cancellation, treat as failure
                    await self._handle_job_failure(job, "Job was unexpectedly cancelled")
                
            except Exception as e:
                error_message = f"Job execution failed: {str(e)}"
                job.last_error = error_message
                await self._handle_job_failure(job, error_message, traceback.format_exc())
            
        finally:
            # Clean up
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
    
    async def _run_job_function(self, job: Job) -> Any:
        """Run the job function with progress tracking."""
        # Create progress updater
        async def update_progress(current: int, total: int, message: str = "", **details):
            job.progress.update(current, total, message, **details)
            
            # Notify progress callbacks
            for callback in self.progress_callbacks:
                try:
                    callback(job.job_id, job.progress)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
        
        # Add progress updater to kwargs if function supports it
        kwargs = job.kwargs.copy()
        if 'progress_callback' in job.function.__code__.co_varnames:
            kwargs['progress_callback'] = update_progress
        
        # Check if function is CPU-intensive (should run in thread pool)
        if hasattr(job.function, '_cpu_intensive') and job.function._cpu_intensive:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.thread_pool,
                lambda: job.function(*job.args, **kwargs)
            )
        else:
            # Run as coroutine or regular function
            if asyncio.iscoroutinefunction(job.function):
                return await job.function(*job.args, **kwargs)
            else:
                return job.function(*job.args, **kwargs)
    
    async def _handle_job_failure(self, job: Job, error_message: str, error_details: str = "") -> None:
        """Handle job failure and retry logic."""
        job.last_error = error_message
        
        if job.should_retry():
            # Schedule retry
            job.status = JobStatus.RETRYING
            job.retry_count += 1
            
            retry_delay = job.calculate_retry_delay()
            
            logger.warning(f"Job {job.job_id} failed, retrying in {retry_delay:.1f}s (attempt {job.retry_count + 1}/{job.max_retries + 1})")
            
            # Schedule retry after delay
            asyncio.create_task(self._schedule_retry(job, retry_delay))
            
            self.stats["jobs_retried"] += 1
        else:
            # Job failed permanently
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.result = JobResult(
                success=False,
                error_message=error_message,
                error_details={"traceback": error_details} if error_details else {}
            )
            
            self.stats["jobs_failed"] += 1
            
            logger.error(f"Job {job.job_id} failed permanently: {error_message}")
            
            # Notify completion callbacks
            for callback in self.completion_callbacks:
                try:
                    callback(job.job_id, job.result)
                except Exception as e:
                    logger.error(f"Error in completion callback: {e}")
    
    async def _schedule_retry(self, job: Job, delay: float) -> None:
        """Schedule a job retry after delay."""
        await asyncio.sleep(delay)
        
        if not job.cancelled and job.status == JobStatus.RETRYING:
            job.status = JobStatus.PENDING
            job.started_at = None
            
            # Re-add to queue
            priority_value = (4 - job.priority.value, time.time())
            await self.pending_queue.put((priority_value, job.job_id))
    
    async def _cleanup_worker(self) -> None:
        """Background worker for cleanup tasks."""
        while not self.shutdown_event.is_set():
            try:
                await self._cleanup_expired_jobs()
                await asyncio.sleep(self.config.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                await asyncio.sleep(self.config.cleanup_interval_seconds)
    
    async def _cleanup_expired_jobs(self) -> None:
        """Clean up expired and old jobs."""
        current_time = datetime.now()
        jobs_to_remove = []
        
        for job_id, job in self.jobs.items():
            # Remove completed jobs older than 24 hours
            if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and
                job.completed_at and 
                current_time - job.completed_at > timedelta(hours=24)):
                jobs_to_remove.append(job_id)
            
            # Cancel expired jobs
            elif job.is_expired() and job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                await self.cancel_job(job_id, "Job expired")
        
        # Remove old jobs
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
            self.completed_jobs.discard(job_id)
        
        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
    
    async def _metrics_worker(self) -> None:
        """Background worker for collecting job metrics."""
        while not self.shutdown_event.is_set():
            try:
                await self._collect_job_metrics()
                await asyncio.sleep(60)  # Collect metrics every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics worker: {e}")
                await asyncio.sleep(60)
    
    async def _collect_job_metrics(self) -> None:
        """Collect job performance metrics by type."""
        for job_type in JobType:
            type_jobs = [job for job in self.jobs.values() if job.job_type == job_type]
            
            if not type_jobs:
                continue
            
            completed_jobs = [job for job in type_jobs if job.status == JobStatus.COMPLETED and job.result]
            failed_jobs = [job for job in type_jobs if job.status == JobStatus.FAILED]
            
            if completed_jobs:
                execution_times = [job.result.execution_time_seconds for job in completed_jobs]
                
                self.job_metrics[job_type] = {
                    "total_jobs": len(type_jobs),
                    "completed_jobs": len(completed_jobs),
                    "failed_jobs": len(failed_jobs),
                    "success_rate": len(completed_jobs) / len(type_jobs) * 100,
                    "average_execution_time": sum(execution_times) / len(execution_times),
                    "min_execution_time": min(execution_times),
                    "max_execution_time": max(execution_times)
                }
    
    async def _save_jobs(self) -> None:
        """Save jobs to persistent storage."""
        try:
            self.config.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Only save jobs that are not completed/failed/cancelled
            jobs_to_save = {
                job_id: job for job_id, job in self.jobs.items()
                if job.status in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRYING]
            }
            
            with open(self.config.persistence_path, 'wb') as f:
                pickle.dump({
                    'jobs': jobs_to_save,
                    'stats': self.stats,
                    'completed_jobs': self.completed_jobs
                }, f)
            
            logger.info(f"Saved {len(jobs_to_save)} jobs to persistence")
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")
    
    async def _load_jobs(self) -> None:
        """Load jobs from persistent storage."""
        if not self.config.persistence_path.exists():
            return
        
        try:
            with open(self.config.persistence_path, 'rb') as f:
                data = pickle.load(f)
            
            self.jobs = data.get('jobs', {})
            self.stats = data.get('stats', self.stats)
            self.completed_jobs = data.get('completed_jobs', set())
            
            # Re-queue pending jobs
            for job_id, job in self.jobs.items():
                if job.status == JobStatus.PENDING:
                    priority_value = (4 - job.priority.value, time.time())
                    await self.pending_queue.put((priority_value, job_id))
            
            logger.info(f"Loaded {len(self.jobs)} jobs from persistence")
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")


def cpu_intensive(func):
    """Decorator to mark a function as CPU-intensive (should run in thread pool)."""
    func._cpu_intensive = True
    return func


def create_job_queue(config: Optional[JobQueueConfig] = None) -> JobQueue:
    """Create a job queue with default or provided configuration."""
    if config is None:
        config = JobQueueConfig()
    return JobQueue(config)