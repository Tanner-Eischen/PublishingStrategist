"""
Progress tracking utilities for WebSocket-enabled analysis progress reporting.
Provides a unified interface for tracking and reporting analysis progress.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from contextlib import asynccontextmanager
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ProgressStatus(Enum):
    """Status of a progress step."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProgressStep:
    """Individual step in a progress workflow."""
    id: str
    name: str
    description: str
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    progress_percentage: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start(self):
        """Mark step as started."""
        self.status = ProgressStatus.IN_PROGRESS
        self.start_time = datetime.now()
        self.progress_percentage = 0.0
    
    def complete(self):
        """Mark step as completed."""
        self.status = ProgressStatus.COMPLETED
        self.end_time = datetime.now()
        self.progress_percentage = 100.0
    
    def fail(self, error_message: str):
        """Mark step as failed."""
        self.status = ProgressStatus.FAILED
        self.end_time = datetime.now()
        self.error_message = error_message
    
    def update_progress(self, percentage: float):
        """Update progress percentage."""
        self.progress_percentage = max(0, min(100, percentage))
    
    @property
    def duration(self) -> Optional[float]:
        """Get step duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

class ProgressTracker:
    """
    Progress tracker that integrates with WebSocket connection manager
    to provide real-time progress updates to clients.
    """
    
    def __init__(self, analysis_id: str, connection_manager=None, total_steps: int = 100):
        self.analysis_id = analysis_id
        self.connection_manager = connection_manager
        self.total_steps = total_steps
        self.current_step = 0
        self.current_progress = 0
        self.status = 'starting'
        self.step_details = {}
        self.start_time = datetime.now()
        self.cancelled = False
        self.paused = False
        
    async def update_progress(self, progress: int, step: int = None, status: str = None, 
                            step_name: str = None, details: Dict[str, Any] = None):
        """Update progress and notify via WebSocket if available."""
        self.current_progress = min(100, max(0, progress))
        
        if step is not None:
            self.current_step = step
            
        if status:
            self.status = status
            
        if step_name:
            self.step_details['current_step_name'] = step_name
            
        if details:
            self.step_details.update(details)
        
        # Calculate estimated time remaining
        if progress > 0 and self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                estimated_total = (elapsed / progress) * 100
                estimated_remaining = max(0, estimated_total - elapsed)
                self.step_details['estimated_remaining'] = estimated_remaining
        
        # Send update via WebSocket if connection manager is available
        if self.connection_manager:
            try:
                await self.connection_manager.update_analysis_progress(
                    self.analysis_id,
                    self.current_progress,
                    self.current_step,
                    self.status,
                    step_details=self.step_details
                )
            except Exception as e:
                logger.error(f"Failed to send progress update: {e}")
    
    async def complete(self, results: Dict[str, Any]):
        """Mark analysis as complete and send results."""
        self.status = 'completed'
        self.current_progress = 100
        
        if self.connection_manager:
            try:
                await self.connection_manager.complete_analysis(self.analysis_id, results)
            except Exception as e:
                logger.error(f"Failed to send completion update: {e}")
    
    async def error(self, error_message: str):
        """Mark analysis as failed and send error."""
        self.status = 'error'
        
        if self.connection_manager:
            try:
                await self.connection_manager.error_analysis(self.analysis_id, error_message)
            except Exception as e:
                logger.error(f"Failed to send error update: {e}")
    
    def is_cancelled(self) -> bool:
        """Check if analysis has been cancelled."""
        if self.connection_manager:
            return self.connection_manager.is_analysis_cancelled(self.analysis_id)
        return self.cancelled
    
    def is_paused(self) -> bool:
        """Check if analysis has been paused."""
        if self.connection_manager:
            return self.connection_manager.is_analysis_paused(self.analysis_id)
        return self.paused
    
    async def wait_if_paused(self):
        """Wait while analysis is paused."""
        while self.is_paused() and not self.is_cancelled():
            await asyncio.sleep(0.5)
    
    def check_cancellation(self):
        """Raise exception if analysis has been cancelled."""
        if self.is_cancelled():
            raise AnalysisCancelledException(f"Analysis {self.analysis_id} was cancelled")

class AnalysisCancelledException(Exception):
    """Exception raised when an analysis is cancelled."""
    pass

class ProgressContext:
    """
    Context manager for progress tracking that automatically handles
    initialization, updates, and cleanup.
    """
    
    def __init__(self, analysis_id: str, connection_manager=None, 
                 analysis_type: str = 'analysis', total_steps: int = 100):
        self.analysis_id = analysis_id
        self.connection_manager = connection_manager
        self.analysis_type = analysis_type
        self.total_steps = total_steps
        self.tracker = None
        
    async def __aenter__(self):
        self.tracker = ProgressTracker(
            self.analysis_id, 
            self.connection_manager, 
            self.total_steps
        )
        
        # Initialize progress
        await self.tracker.update_progress(0, 0, 'starting')
        return self.tracker
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Normal completion - this should be handled by the analysis function
            pass
        elif exc_type == AnalysisCancelledException:
            # Analysis was cancelled - already handled
            pass
        else:
            # Error occurred
            error_message = str(exc_val) if exc_val else "Unknown error occurred"
            await self.tracker.error(error_message)
        
        return False  # Don't suppress exceptions

def progress_tracked(analysis_type: str, total_steps: int = 100):
    """
    Decorator for analysis functions to automatically add progress tracking.
    
    Usage:
        @progress_tracked('niche_discovery', 6)
        async def discover_niches(tracker, keywords, **kwargs):
            await tracker.update_progress(10, 1, 'in-progress', 'Expanding keywords')
            # ... analysis logic ...
            await tracker.complete(results)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract analysis_id and connection_manager from kwargs
            analysis_id = kwargs.pop('analysis_id', None)
            connection_manager = kwargs.pop('connection_manager', None)
            
            if not analysis_id:
                # If no analysis_id provided, run without progress tracking
                return await func(None, *args, **kwargs)
            
            async with ProgressContext(analysis_id, connection_manager, analysis_type, total_steps) as tracker:
                return await func(tracker, *args, **kwargs)
        
        return wrapper
    return decorator

class StepProgressTracker:
    """
    Helper class for tracking progress through a series of predefined steps.
    """
    
    def __init__(self, tracker: ProgressTracker, steps: list):
        self.tracker = tracker
        self.steps = steps
        self.current_step_index = 0
        
    async def next_step(self, details: Dict[str, Any] = None):
        """Move to the next step and update progress."""
        if self.current_step_index < len(self.steps):
            step_name = self.steps[self.current_step_index]
            progress = int((self.current_step_index / len(self.steps)) * 100)
            
            await self.tracker.update_progress(
                progress, 
                self.current_step_index, 
                'in-progress',
                step_name,
                details
            )
            
            self.current_step_index += 1
            
            # Check for cancellation after each step
            self.tracker.check_cancellation()
            await self.tracker.wait_if_paused()
    
    async def complete_step(self, step_index: int = None, details: Dict[str, Any] = None):
        """Mark a specific step as complete."""
        if step_index is None:
            step_index = self.current_step_index - 1
            
        if 0 <= step_index < len(self.steps):
            step_name = self.steps[step_index]
            progress = int(((step_index + 1) / len(self.steps)) * 100)
            
            step_details = details or {}
            step_details['completed_step'] = step_name
            
            await self.tracker.update_progress(
                progress,
                step_index,
                'in-progress',
                step_name,
                step_details
            )
    
    async def finish(self, results: Dict[str, Any]):
        """Complete all steps and finish the analysis."""
        await self.tracker.update_progress(100, len(self.steps), 'completed')
        await self.tracker.complete(results)

# Utility functions for common progress patterns

async def with_progress_steps(tracker: ProgressTracker, steps: list, step_function: Callable):
    """
    Execute a function for each step with automatic progress tracking.
    
    Args:
        tracker: Progress tracker instance
        steps: List of step names/descriptions
        step_function: Async function that takes (step_index, step_name, tracker)
    """
    step_tracker = StepProgressTracker(tracker, steps)
    
    for i, step_name in enumerate(steps):
        await step_tracker.next_step()
        
        try:
            result = await step_function(i, step_name, tracker)
            await step_tracker.complete_step(i, {'result': result})
        except Exception as e:
            await tracker.error(f"Error in step '{step_name}': {str(e)}")
            raise

async def simulate_progress(tracker: ProgressTracker, duration: float = 5.0, steps: int = 10):
    """
    Simulate progress for testing purposes.
    
    Args:
        tracker: Progress tracker instance
        duration: Total duration in seconds
        steps: Number of progress steps
    """
    step_duration = duration / steps
    
    for i in range(steps):
        progress = int((i / steps) * 100)
        await tracker.update_progress(
            progress, 
            i, 
            'in-progress',
            f'Processing step {i + 1}/{steps}',
            {'step_duration': step_duration}
        )
        
        # Check for cancellation
        tracker.check_cancellation()
        await tracker.wait_if_paused()
        
        # Simulate work
        await asyncio.sleep(step_duration)
    
    # Complete
    await tracker.update_progress(100, steps, 'completed')

# Integration helpers for existing analysis tools

def get_connection_manager():
    """Get the global connection manager instance."""
    try:
        from api.main import manager
        return manager
    except ImportError:
        logger.warning("Connection manager not available - progress tracking disabled")
        return None

async def create_progress_tracker(analysis_id: str, analysis_type: str = 'analysis') -> ProgressTracker:
    """Create a progress tracker with the global connection manager."""
    connection_manager = get_connection_manager()
    return ProgressTracker(analysis_id, connection_manager)

# Export main classes and functions
__all__ = [
    'ProgressTracker',
    'ProgressContext', 
    'StepProgressTracker',
    'AnalysisCancelledException',
    'progress_tracked',
    'with_progress_steps',
    'simulate_progress',
    'get_connection_manager',
    'create_progress_tracker'
]