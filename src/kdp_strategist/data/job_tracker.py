"""Job status tracking and progress reporting system.

This module provides real-time job tracking, progress reporting,
and WebSocket-based updates for the frontend.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import weakref
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ProgressEventType(Enum):
    """Types of progress events."""
    JOB_STARTED = "job_started"
    JOB_PROGRESS = "job_progress"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    JOB_RETRYING = "job_retrying"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    MILESTONE_REACHED = "milestone_reached"


@dataclass
class ProgressEvent:
    """Represents a progress event."""
    event_id: str
    job_id: str
    event_type: ProgressEventType
    timestamp: datetime
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "job_id": self.job_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "data": self.data
        }


@dataclass
class JobTrackingInfo:
    """Extended job tracking information."""
    job_id: str
    job_type: str
    status: str
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress tracking
    current_step: int = 0
    total_steps: int = 0
    percentage: float = 0.0
    current_message: str = ""
    
    # Performance metrics
    execution_time_seconds: float = 0.0
    estimated_remaining_seconds: Optional[float] = None
    
    # Error tracking
    retry_count: int = 0
    max_retries: int = 0
    last_error: Optional[str] = None
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    
    # Events history
    events: List[ProgressEvent] = field(default_factory=list)
    
    def add_event(self, event: ProgressEvent) -> None:
        """Add a progress event."""
        self.events.append(event)
        # Keep only recent events (last 100)
        if len(self.events) > 100:
            self.events = self.events[-100:]
    
    def get_recent_events(self, limit: int = 10) -> List[ProgressEvent]:
        """Get recent events."""
        return self.events[-limit:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": {
                "current_step": self.current_step,
                "total_steps": self.total_steps,
                "percentage": self.percentage,
                "message": self.current_message
            },
            "performance": {
                "execution_time_seconds": self.execution_time_seconds,
                "estimated_remaining_seconds": self.estimated_remaining_seconds
            },
            "error_info": {
                "retry_count": self.retry_count,
                "max_retries": self.max_retries,
                "last_error": self.last_error
            },
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "recent_events": [event.to_dict() for event in self.get_recent_events()]
        }


@dataclass
class JobTrackerConfig:
    """Configuration for job tracker."""
    max_tracked_jobs: int = 1000
    event_history_limit: int = 10000
    cleanup_interval_seconds: int = 300
    websocket_enabled: bool = True
    websocket_port: int = 8765
    enable_performance_analytics: bool = True
    enable_real_time_updates: bool = True


class JobTracker:
    """Job status tracking and progress reporting system."""
    
    def __init__(self, config: JobTrackerConfig):
        self.config = config
        self.tracked_jobs: Dict[str, JobTrackingInfo] = {}
        self.event_history: deque = deque(maxlen=config.event_history_limit)
        
        # WebSocket connections for real-time updates
        self.websocket_connections: Set[Any] = set()
        self.websocket_server: Optional[Any] = None
        
        # Event subscribers
        self.event_subscribers: List[Callable[[ProgressEvent], None]] = []
        self.job_subscribers: Dict[str, List[Callable[[JobTrackingInfo], None]]] = defaultdict(list)
        
        # Performance analytics
        self.job_performance: Dict[str, List[float]] = defaultdict(list)  # job_type -> execution_times
        self.step_performance: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.websocket_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_jobs_tracked": 0,
            "active_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "total_events": 0,
            "websocket_connections": 0
        }
    
    async def start(self) -> None:
        """Start the job tracker."""
        logger.info("Starting job tracker")
        
        # Start background tasks
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        # Start WebSocket server if enabled
        if self.config.websocket_enabled:
            self.websocket_task = asyncio.create_task(self._start_websocket_server())
        
        logger.info("Job tracker started")
    
    async def stop(self) -> None:
        """Stop the job tracker."""
        logger.info("Stopping job tracker")
        
        # Stop background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.websocket_task:
            self.websocket_task.cancel()
        
        # Close WebSocket connections
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        logger.info("Job tracker stopped")
    
    def track_job(self, job_id: str, job_type: str, status: str, priority: int = 2,
                  dependencies: Optional[List[str]] = None) -> JobTrackingInfo:
        """Start tracking a job."""
        tracking_info = JobTrackingInfo(
            job_id=job_id,
            job_type=job_type,
            status=status,
            priority=priority,
            created_at=datetime.now(),
            dependencies=dependencies or []
        )
        
        self.tracked_jobs[job_id] = tracking_info
        self.stats["total_jobs_tracked"] += 1
        self.stats["active_jobs"] += 1
        
        # Create job started event
        event = ProgressEvent(
            event_id=f"{job_id}_started_{datetime.now().timestamp()}",
            job_id=job_id,
            event_type=ProgressEventType.JOB_STARTED,
            timestamp=datetime.now(),
            message=f"Job {job_type} started",
            data={"job_type": job_type, "priority": priority}
        )
        
        self._add_event(event)
        
        logger.info(f"Started tracking job {job_id} ({job_type})")
        return tracking_info
    
    def update_job_progress(self, job_id: str, current_step: int, total_steps: int,
                           message: str = "", **additional_data) -> None:
        """Update job progress."""
        if job_id not in self.tracked_jobs:
            logger.warning(f"Attempted to update progress for untracked job: {job_id}")
            return
        
        tracking_info = self.tracked_jobs[job_id]
        tracking_info.current_step = current_step
        tracking_info.total_steps = total_steps
        tracking_info.percentage = (current_step / total_steps * 100) if total_steps > 0 else 0.0
        tracking_info.current_message = message
        
        # Calculate estimated remaining time
        if tracking_info.started_at and current_step > 0:
            elapsed_time = (datetime.now() - tracking_info.started_at).total_seconds()
            time_per_step = elapsed_time / current_step
            remaining_steps = total_steps - current_step
            tracking_info.estimated_remaining_seconds = time_per_step * remaining_steps
        
        # Create progress event
        event = ProgressEvent(
            event_id=f"{job_id}_progress_{datetime.now().timestamp()}",
            job_id=job_id,
            event_type=ProgressEventType.JOB_PROGRESS,
            timestamp=datetime.now(),
            message=message or f"Step {current_step}/{total_steps}",
            data={
                "current_step": current_step,
                "total_steps": total_steps,
                "percentage": tracking_info.percentage,
                **additional_data
            }
        )
        
        self._add_event(event)
        
        # Notify subscribers
        self._notify_job_subscribers(job_id, tracking_info)
    
    def update_job_status(self, job_id: str, status: str, message: str = "",
                         error_message: Optional[str] = None) -> None:
        """Update job status."""
        if job_id not in self.tracked_jobs:
            logger.warning(f"Attempted to update status for untracked job: {job_id}")
            return
        
        tracking_info = self.tracked_jobs[job_id]
        old_status = tracking_info.status
        tracking_info.status = status
        
        # Update timestamps
        if status == "running" and not tracking_info.started_at:
            tracking_info.started_at = datetime.now()
        elif status in ["completed", "failed", "cancelled"]:
            tracking_info.completed_at = datetime.now()
            if tracking_info.started_at:
                tracking_info.execution_time_seconds = (
                    tracking_info.completed_at - tracking_info.started_at
                ).total_seconds()
            
            # Update statistics
            self.stats["active_jobs"] -= 1
            if status == "completed":
                self.stats["completed_jobs"] += 1
            elif status == "failed":
                self.stats["failed_jobs"] += 1
            elif status == "cancelled":
                self.stats["cancelled_jobs"] += 1
        
        # Handle error information
        if error_message:
            tracking_info.last_error = error_message
        
        # Handle retry status
        if status == "retrying":
            tracking_info.retry_count += 1
        
        # Determine event type
        event_type_map = {
            "completed": ProgressEventType.JOB_COMPLETED,
            "failed": ProgressEventType.JOB_FAILED,
            "cancelled": ProgressEventType.JOB_CANCELLED,
            "retrying": ProgressEventType.JOB_RETRYING
        }
        
        event_type = event_type_map.get(status, ProgressEventType.JOB_PROGRESS)
        
        # Create status event
        event = ProgressEvent(
            event_id=f"{job_id}_status_{datetime.now().timestamp()}",
            job_id=job_id,
            event_type=event_type,
            timestamp=datetime.now(),
            message=message or f"Job status changed to {status}",
            data={
                "old_status": old_status,
                "new_status": status,
                "error_message": error_message,
                "execution_time": tracking_info.execution_time_seconds
            }
        )
        
        self._add_event(event)
        
        # Record performance data
        if status == "completed" and self.config.enable_performance_analytics:
            self.job_performance[tracking_info.job_type].append(tracking_info.execution_time_seconds)
        
        # Notify subscribers
        self._notify_job_subscribers(job_id, tracking_info)
        
        logger.info(f"Job {job_id} status updated: {old_status} -> {status}")
    
    def add_job_milestone(self, job_id: str, milestone: str, message: str = "",
                         **additional_data) -> None:
        """Add a milestone event for a job."""
        if job_id not in self.tracked_jobs:
            return
        
        event = ProgressEvent(
            event_id=f"{job_id}_milestone_{datetime.now().timestamp()}",
            job_id=job_id,
            event_type=ProgressEventType.MILESTONE_REACHED,
            timestamp=datetime.now(),
            message=message or f"Milestone reached: {milestone}",
            data={"milestone": milestone, **additional_data}
        )
        
        self._add_event(event)
    
    def add_step_event(self, job_id: str, step_name: str, event_type: ProgressEventType,
                      message: str = "", **additional_data) -> None:
        """Add a step-level event."""
        if job_id not in self.tracked_jobs:
            return
        
        event = ProgressEvent(
            event_id=f"{job_id}_step_{datetime.now().timestamp()}",
            job_id=job_id,
            event_type=event_type,
            timestamp=datetime.now(),
            message=message or f"Step {step_name}: {event_type.value}",
            data={"step_name": step_name, **additional_data}
        )
        
        self._add_event(event)
    
    def get_job_info(self, job_id: str) -> Optional[JobTrackingInfo]:
        """Get job tracking information."""
        return self.tracked_jobs.get(job_id)
    
    def get_active_jobs(self) -> List[JobTrackingInfo]:
        """Get all active jobs."""
        return [
            job for job in self.tracked_jobs.values()
            if job.status in ["pending", "running", "retrying"]
        ]
    
    def get_job_history(self, limit: int = 100, job_type: Optional[str] = None) -> List[JobTrackingInfo]:
        """Get job history."""
        jobs = list(self.tracked_jobs.values())
        
        # Filter by job type if specified
        if job_type:
            jobs = [job for job in jobs if job.job_type == job_type]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return jobs[:limit]
    
    def get_job_events(self, job_id: str, limit: int = 50) -> List[ProgressEvent]:
        """Get events for a specific job."""
        if job_id not in self.tracked_jobs:
            return []
        
        return self.tracked_jobs[job_id].get_recent_events(limit)
    
    def get_recent_events(self, limit: int = 100, event_type: Optional[ProgressEventType] = None) -> List[ProgressEvent]:
        """Get recent events across all jobs."""
        events = list(self.event_history)
        
        # Filter by event type if specified
        if event_type:
            events = [event for event in events if event.event_type == event_type]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        return events[:limit]
    
    def get_performance_analytics(self) -> Dict[str, Any]:
        """Get performance analytics."""
        if not self.config.enable_performance_analytics:
            return {"error": "Performance analytics disabled"}
        
        analytics = {
            "job_type_performance": {},
            "overall_stats": self.stats.copy(),
            "active_jobs_count": len(self.get_active_jobs())
        }
        
        # Calculate performance metrics by job type
        for job_type, execution_times in self.job_performance.items():
            if execution_times:
                analytics["job_type_performance"][job_type] = {
                    "total_jobs": len(execution_times),
                    "average_execution_time": sum(execution_times) / len(execution_times),
                    "min_execution_time": min(execution_times),
                    "max_execution_time": max(execution_times),
                    "recent_average": sum(execution_times[-10:]) / min(len(execution_times), 10)
                }
        
        return analytics
    
    def subscribe_to_job(self, job_id: str, callback: Callable[[JobTrackingInfo], None]) -> None:
        """Subscribe to updates for a specific job."""
        self.job_subscribers[job_id].append(callback)
    
    def subscribe_to_events(self, callback: Callable[[ProgressEvent], None]) -> None:
        """Subscribe to all progress events."""
        self.event_subscribers.append(callback)
    
    def unsubscribe_from_job(self, job_id: str, callback: Callable[[JobTrackingInfo], None]) -> None:
        """Unsubscribe from job updates."""
        if job_id in self.job_subscribers:
            try:
                self.job_subscribers[job_id].remove(callback)
            except ValueError:
                pass
    
    def _add_event(self, event: ProgressEvent) -> None:
        """Add an event to the history and notify subscribers."""
        self.event_history.append(event)
        self.stats["total_events"] += 1
        
        # Add event to job's event history
        if event.job_id in self.tracked_jobs:
            self.tracked_jobs[event.job_id].add_event(event)
        
        # Notify event subscribers
        for callback in self.event_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event subscriber callback: {e}")
        
        # Send to WebSocket connections
        if self.config.websocket_enabled:
            asyncio.create_task(self._broadcast_event(event))
    
    def _notify_job_subscribers(self, job_id: str, tracking_info: JobTrackingInfo) -> None:
        """Notify subscribers of job updates."""
        for callback in self.job_subscribers.get(job_id, []):
            try:
                callback(tracking_info)
            except Exception as e:
                logger.error(f"Error in job subscriber callback: {e}")
    
    async def _broadcast_event(self, event: ProgressEvent) -> None:
        """Broadcast event to WebSocket connections."""
        if not self.websocket_connections:
            return
        
        message = json.dumps(event.to_dict())
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.websocket_connections.copy():
            try:
                await websocket.send(message)
            except Exception:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected
        self.stats["websocket_connections"] = len(self.websocket_connections)
    
    async def _start_websocket_server(self) -> None:
        """Start WebSocket server for real-time updates."""
        try:
            import websockets
            
            async def handle_websocket(websocket, path):
                """Handle WebSocket connection."""
                self.websocket_connections.add(websocket)
                self.stats["websocket_connections"] = len(self.websocket_connections)
                
                logger.info(f"WebSocket client connected from {websocket.remote_address}")
                
                try:
                    # Send current job status on connection
                    active_jobs = self.get_active_jobs()
                    for job in active_jobs:
                        message = json.dumps({
                            "type": "job_status",
                            "data": job.to_dict()
                        })
                        await websocket.send(message)
                    
                    # Keep connection alive
                    await websocket.wait_closed()
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                finally:
                    self.websocket_connections.discard(websocket)
                    self.stats["websocket_connections"] = len(self.websocket_connections)
            
            self.websocket_server = await websockets.serve(
                handle_websocket,
                "localhost",
                self.config.websocket_port
            )
            
            logger.info(f"WebSocket server started on port {self.config.websocket_port}")
            
        except ImportError:
            logger.warning("websockets library not available, WebSocket support disabled")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def _cleanup_worker(self) -> None:
        """Background worker for cleanup tasks."""
        while True:
            try:
                await self._cleanup_old_jobs()
                await asyncio.sleep(self.config.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                await asyncio.sleep(self.config.cleanup_interval_seconds)
    
    async def _cleanup_old_jobs(self) -> None:
        """Clean up old completed jobs."""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=24)  # Keep jobs for 24 hours
        
        jobs_to_remove = []
        for job_id, job in self.tracked_jobs.items():
            if (job.status in ["completed", "failed", "cancelled"] and
                job.completed_at and job.completed_at < cutoff_time):
                jobs_to_remove.append(job_id)
        
        # Remove old jobs
        for job_id in jobs_to_remove:
            del self.tracked_jobs[job_id]
            if job_id in self.job_subscribers:
                del self.job_subscribers[job_id]
        
        # Limit total tracked jobs
        if len(self.tracked_jobs) > self.config.max_tracked_jobs:
            # Remove oldest completed jobs
            completed_jobs = [
                (job_id, job) for job_id, job in self.tracked_jobs.items()
                if job.status in ["completed", "failed", "cancelled"]
            ]
            completed_jobs.sort(key=lambda x: x[1].completed_at or datetime.min)
            
            excess_count = len(self.tracked_jobs) - self.config.max_tracked_jobs
            for job_id, _ in completed_jobs[:excess_count]:
                del self.tracked_jobs[job_id]
                if job_id in self.job_subscribers:
                    del self.job_subscribers[job_id]
        
        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old job records")


def create_job_tracker(config: Optional[JobTrackerConfig] = None) -> JobTracker:
    """Create a job tracker with default or provided configuration."""
    if config is None:
        config = JobTrackerConfig()
    return JobTracker(config)