"""Cache warming system for KDP Strategist.

This module implements intelligent cache warming strategies to preload
frequently requested data and improve cache hit rates.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class WarmingStrategy(Enum):
    """Different cache warming strategies."""
    POPULAR_KEYWORDS = "popular_keywords"
    TRENDING_NICHES = "trending_niches"
    RECENT_SEARCHES = "recent_searches"
    SEASONAL_DATA = "seasonal_data"
    COMPETITOR_DATA = "competitor_data"
    USER_PREFERENCES = "user_preferences"


@dataclass
class WarmingJob:
    """Represents a cache warming job."""
    strategy: WarmingStrategy
    priority: int
    data_keys: List[str]
    callback: Callable[[], Dict[str, Any]]
    schedule: str  # cron-like schedule
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    max_runtime_seconds: int = 300


@dataclass
class WarmingConfig:
    """Configuration for cache warming system."""
    enabled: bool = True
    max_concurrent_jobs: int = 3
    job_timeout_seconds: int = 300
    warming_schedule_file: Path = Path("cache/warming_schedule.json")
    popular_keywords_limit: int = 100
    trending_niches_limit: int = 50
    recent_searches_days: int = 7
    seasonal_data_months: int = 12


class CacheWarmingManager:
    """Manages cache warming operations and strategies."""
    
    def __init__(self, cache_manager, config: WarmingConfig):
        self.cache_manager = cache_manager
        self.config = config
        self.warming_jobs: Dict[str, WarmingJob] = {}
        self.running_jobs: Set[str] = set()
        self.job_history: List[Dict[str, Any]] = []
        
        # Data sources for warming
        self.popular_keywords: List[str] = []
        self.trending_niches: List[str] = []
        self.recent_searches: List[str] = []
        self.user_preferences: Dict[str, Any] = {}
        
        # Background task
        self.warming_task: Optional[asyncio.Task] = None
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Initialize warming jobs
        self._initialize_warming_jobs()
    
    def _initialize_warming_jobs(self) -> None:
        """Initialize default warming jobs."""
        # Popular keywords warming
        self.warming_jobs["popular_keywords"] = WarmingJob(
            strategy=WarmingStrategy.POPULAR_KEYWORDS,
            priority=1,
            data_keys=["trends", "competition"],
            callback=self._warm_popular_keywords,
            schedule="0 */6 * * *",  # Every 6 hours
            max_runtime_seconds=600
        )
        
        # Trending niches warming
        self.warming_jobs["trending_niches"] = WarmingJob(
            strategy=WarmingStrategy.TRENDING_NICHES,
            priority=2,
            data_keys=["niche_analysis", "profitability"],
            callback=self._warm_trending_niches,
            schedule="0 */12 * * *",  # Every 12 hours
            max_runtime_seconds=900
        )
        
        # Recent searches warming
        self.warming_jobs["recent_searches"] = WarmingJob(
            strategy=WarmingStrategy.RECENT_SEARCHES,
            priority=3,
            data_keys=["search_results", "related_keywords"],
            callback=self._warm_recent_searches,
            schedule="0 */4 * * *",  # Every 4 hours
            max_runtime_seconds=300
        )
        
        # Seasonal data warming
        self.warming_jobs["seasonal_data"] = WarmingJob(
            strategy=WarmingStrategy.SEASONAL_DATA,
            priority=4,
            data_keys=["seasonal_trends", "holiday_keywords"],
            callback=self._warm_seasonal_data,
            schedule="0 0 * * 0",  # Weekly on Sunday
            max_runtime_seconds=1200
        )
        
        # Load custom warming jobs from file
        self._load_warming_schedule()
    
    async def start_warming(self) -> None:
        """Start the cache warming system."""
        if not self.config.enabled:
            logger.info("Cache warming is disabled")
            return
        
        logger.info("Starting cache warming system")
        
        # Start background tasks
        self.warming_task = asyncio.create_task(self._warming_worker())
        self.scheduler_task = asyncio.create_task(self._scheduler_worker())
        
        # Initial warming for critical data
        await self._initial_warming()
    
    async def stop_warming(self) -> None:
        """Stop the cache warming system."""
        logger.info("Stopping cache warming system")
        
        if self.warming_task:
            self.warming_task.cancel()
        if self.scheduler_task:
            self.scheduler_task.cancel()
        
        # Wait for running jobs to complete
        while self.running_jobs:
            await asyncio.sleep(1)
    
    async def _initial_warming(self) -> None:
        """Perform initial cache warming for critical data."""
        logger.info("Performing initial cache warming")
        
        # Warm high-priority jobs immediately
        high_priority_jobs = [
            job for job in self.warming_jobs.values()
            if job.priority <= 2 and job.enabled
        ]
        
        for job in high_priority_jobs:
            await self._execute_warming_job(job.strategy.value)
    
    async def _warming_worker(self) -> None:
        """Background worker for cache warming operations."""
        while True:
            try:
                # Check for jobs that need to run
                jobs_to_run = self._get_jobs_to_run()
                
                # Execute jobs with concurrency limit
                semaphore = asyncio.Semaphore(self.config.max_concurrent_jobs)
                tasks = []
                
                for job_id in jobs_to_run:
                    if job_id not in self.running_jobs:
                        task = asyncio.create_task(
                            self._execute_warming_job_with_semaphore(semaphore, job_id)
                        )
                        tasks.append(task)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Sleep before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in warming worker: {e}")
                await asyncio.sleep(60)
    
    async def _scheduler_worker(self) -> None:
        """Background worker for job scheduling."""
        while True:
            try:
                # Update next run times for all jobs
                for job_id, job in self.warming_jobs.items():
                    if job.enabled and job.next_run is None:
                        job.next_run = self._calculate_next_run(job.schedule)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler worker: {e}")
                await asyncio.sleep(300)
    
    def _get_jobs_to_run(self) -> List[str]:
        """Get list of jobs that should run now."""
        now = datetime.now()
        jobs_to_run = []
        
        for job_id, job in self.warming_jobs.items():
            if (job.enabled and 
                job.next_run and 
                now >= job.next_run and 
                job_id not in self.running_jobs):
                jobs_to_run.append(job_id)
        
        # Sort by priority
        jobs_to_run.sort(key=lambda x: self.warming_jobs[x].priority)
        
        return jobs_to_run
    
    async def _execute_warming_job_with_semaphore(self, semaphore: asyncio.Semaphore, job_id: str) -> None:
        """Execute warming job with concurrency control."""
        async with semaphore:
            await self._execute_warming_job(job_id)
    
    async def _execute_warming_job(self, job_id: str) -> None:
        """Execute a specific warming job."""
        if job_id not in self.warming_jobs:
            logger.error(f"Unknown warming job: {job_id}")
            return
        
        job = self.warming_jobs[job_id]
        self.running_jobs.add(job_id)
        
        start_time = datetime.now()
        success = False
        error_message = None
        items_warmed = 0
        
        try:
            logger.info(f"Starting warming job: {job_id}")
            
            # Execute job with timeout
            data = await asyncio.wait_for(
                asyncio.to_thread(job.callback),
                timeout=job.max_runtime_seconds
            )
            
            # Warm cache with the data
            if data:
                for key, value in data.items():
                    await self.cache_manager.set(
                        key, 
                        value, 
                        ttl=3600,  # 1 hour TTL for warmed data
                        priority=self.cache_manager.CachePriority.HIGH,
                        tags={"warmed", job.strategy.value}
                    )
                    items_warmed += 1
            
            success = True
            logger.info(f"Completed warming job: {job_id} ({items_warmed} items)")
            
        except asyncio.TimeoutError:
            error_message = f"Job timed out after {job.max_runtime_seconds} seconds"
            logger.error(f"Warming job {job_id} timed out")
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error in warming job {job_id}: {e}")
        finally:
            # Update job status
            job.last_run = start_time
            job.next_run = self._calculate_next_run(job.schedule)
            
            # Record job history
            self.job_history.append({
                "job_id": job_id,
                "strategy": job.strategy.value,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "success": success,
                "items_warmed": items_warmed,
                "error_message": error_message
            })
            
            # Keep only recent history
            if len(self.job_history) > 1000:
                self.job_history = self.job_history[-1000:]
            
            self.running_jobs.discard(job_id)
    
    def _warm_popular_keywords(self) -> Dict[str, Any]:
        """Warm cache with popular keywords data."""
        logger.info("Warming popular keywords")
        
        # This would typically fetch from analytics or database
        popular_keywords = [
            "kindle publishing", "self publishing", "book marketing",
            "amazon kdp", "book cover design", "book formatting",
            "author platform", "book promotion", "publishing tips",
            "indie author", "book sales", "royalties", "book launch",
            "manuscript", "editing", "proofreading", "isbn",
            "book distribution", "print on demand", "ebook",
            "audiobook", "book reviews", "bestseller", "genre fiction",
            "non-fiction", "memoir", "biography", "cookbook",
            "children's books", "young adult", "romance", "mystery",
            "thriller", "science fiction", "fantasy", "horror",
            "historical fiction", "literary fiction", "poetry",
            "self-help", "business", "health", "fitness", "travel",
            "education", "textbook", "reference", "how-to",
            "crafts", "hobbies", "religion", "spirituality"
        ]
        
        warmed_data = {}
        
        # Cache warming for trends will be done through real API calls
        # when the trends client is used, not through mock data
        logger.info(f"Trends cache warming disabled - using real API data only")
        
        return warmed_data
    
    def _warm_trending_niches(self) -> Dict[str, Any]:
        """Warm cache with trending niches data."""
        logger.info("Warming trending niches")
        
        trending_niches = [
            "AI and Machine Learning", "Sustainable Living", "Remote Work",
            "Digital Marketing", "Cryptocurrency", "Mental Health",
            "Plant-Based Cooking", "Home Organization", "Minimalism",
            "Personal Finance", "Productivity", "Meditation",
            "Urban Gardening", "DIY Crafts", "Pet Care",
            "Travel Hacking", "Photography", "Fitness",
            "Parenting", "Relationships", "Career Development",
            "Entrepreneurship", "Investing", "Real Estate",
            "Technology", "Gaming", "Music", "Art",
            "Fashion", "Beauty", "Health", "Nutrition"
        ]
        
        warmed_data = {}
        
        # Cache warming for trending niches will be done through real API analysis
        # when the niche discovery system is used, not through mock data
        logger.info(f"Trending niches cache warming disabled - using real analysis data only")
        
        return warmed_data
    
    def _warm_recent_searches(self) -> Dict[str, Any]:
        """Warm cache with recent search data."""
        logger.info("Warming recent searches")
        
        # This would typically come from user analytics
        recent_searches = [
            "low content books", "journal prompts", "coloring books",
            "planners", "notebooks", "activity books", "puzzle books",
            "workbooks", "logbooks", "trackers", "calendars",
            "recipe books", "photo books", "scrapbooks", "albums"
        ]
        
        warmed_data = {}
        
        # Cache warming for recent searches will be done through real user analytics
        # and actual search results, not through mock data
        logger.info(f"Recent searches cache warming disabled - using real user data only")
        
        return warmed_data
    
    def _warm_seasonal_data(self) -> Dict[str, Any]:
        """Warm cache with seasonal trend data."""
        logger.info("Warming seasonal data")
        
        current_month = datetime.now().month
        seasonal_keywords = {
            1: ["new year", "resolutions", "planning", "goals"],
            2: ["valentine", "love", "romance", "relationships"],
            3: ["spring", "gardening", "cleaning", "renewal"],
            4: ["easter", "spring break", "taxes", "organization"],
            5: ["mother's day", "graduation", "spring", "flowers"],
            6: ["father's day", "summer", "vacation", "travel"],
            7: ["summer", "vacation", "outdoor", "bbq"],
            8: ["back to school", "organization", "planning", "education"],
            9: ["fall", "autumn", "harvest", "school"],
            10: ["halloween", "horror", "spooky", "costumes"],
            11: ["thanksgiving", "gratitude", "family", "cooking"],
            12: ["christmas", "holiday", "gifts", "winter"]
        }
        
        warmed_data = {}
        
        # Warm current month and next month
        for month_offset in [0, 1]:
            target_month = ((current_month + month_offset - 1) % 12) + 1
            keywords = seasonal_keywords.get(target_month, [])
            
            # Cache warming for seasonal data will be done through real Google Trends API
            # seasonal analysis, not through mock data
            logger.info(f"Seasonal trends cache warming disabled for month {target_month} - using real trends data only")
        
        return warmed_data
    
    def _calculate_next_run(self, schedule: str) -> datetime:
        """Calculate next run time based on cron-like schedule."""
        # Simplified cron parser - in production, use a proper cron library
        # Format: "minute hour day month weekday"
        # Example: "0 */6 * * *" = every 6 hours
        
        now = datetime.now()
        
        if schedule == "0 */6 * * *":  # Every 6 hours
            next_run = now.replace(minute=0, second=0, microsecond=0)
            while next_run <= now:
                next_run += timedelta(hours=6)
            return next_run
        
        elif schedule == "0 */12 * * *":  # Every 12 hours
            next_run = now.replace(minute=0, second=0, microsecond=0)
            while next_run <= now:
                next_run += timedelta(hours=12)
            return next_run
        
        elif schedule == "0 */4 * * *":  # Every 4 hours
            next_run = now.replace(minute=0, second=0, microsecond=0)
            while next_run <= now:
                next_run += timedelta(hours=4)
            return next_run
        
        elif schedule == "0 0 * * 0":  # Weekly on Sunday
            next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0 and now.hour > 0:
                days_until_sunday = 7
            next_run += timedelta(days=days_until_sunday)
            return next_run
        
        else:
            # Default: run in 1 hour
            return now + timedelta(hours=1)
    
    def _load_warming_schedule(self) -> None:
        """Load warming schedule from file."""
        if not self.config.warming_schedule_file.exists():
            return
        
        try:
            with open(self.config.warming_schedule_file, 'r') as f:
                schedule_data = json.load(f)
            
            for job_id, job_config in schedule_data.items():
                if job_id in self.warming_jobs:
                    job = self.warming_jobs[job_id]
                    job.enabled = job_config.get('enabled', job.enabled)
                    job.schedule = job_config.get('schedule', job.schedule)
                    job.priority = job_config.get('priority', job.priority)
                    job.max_runtime_seconds = job_config.get('max_runtime_seconds', job.max_runtime_seconds)
            
            logger.info(f"Loaded warming schedule from {self.config.warming_schedule_file}")
        except Exception as e:
            logger.error(f"Failed to load warming schedule: {e}")
    
    def save_warming_schedule(self) -> None:
        """Save current warming schedule to file."""
        try:
            self.config.warming_schedule_file.parent.mkdir(parents=True, exist_ok=True)
            
            schedule_data = {}
            for job_id, job in self.warming_jobs.items():
                schedule_data[job_id] = {
                    'enabled': job.enabled,
                    'schedule': job.schedule,
                    'priority': job.priority,
                    'max_runtime_seconds': job.max_runtime_seconds,
                    'strategy': job.strategy.value
                }
            
            with open(self.config.warming_schedule_file, 'w') as f:
                json.dump(schedule_data, f, indent=2)
            
            logger.info(f"Saved warming schedule to {self.config.warming_schedule_file}")
        except Exception as e:
            logger.error(f"Failed to save warming schedule: {e}")
    
    async def add_custom_warming_job(self, 
                                   job_id: str,
                                   strategy: WarmingStrategy,
                                   callback: Callable[[], Dict[str, Any]],
                                   schedule: str,
                                   priority: int = 5) -> None:
        """Add a custom warming job."""
        self.warming_jobs[job_id] = WarmingJob(
            strategy=strategy,
            priority=priority,
            data_keys=[],
            callback=callback,
            schedule=schedule
        )
        
        logger.info(f"Added custom warming job: {job_id}")
    
    async def remove_warming_job(self, job_id: str) -> bool:
        """Remove a warming job."""
        if job_id in self.warming_jobs:
            del self.warming_jobs[job_id]
            logger.info(f"Removed warming job: {job_id}")
            return True
        return False
    
    async def trigger_warming_job(self, job_id: str) -> bool:
        """Manually trigger a warming job."""
        if job_id in self.warming_jobs and job_id not in self.running_jobs:
            await self._execute_warming_job(job_id)
            return True
        return False
    
    def get_warming_status(self) -> Dict[str, Any]:
        """Get current warming system status."""
        return {
            "enabled": self.config.enabled,
            "total_jobs": len(self.warming_jobs),
            "running_jobs": len(self.running_jobs),
            "job_status": {
                job_id: {
                    "strategy": job.strategy.value,
                    "priority": job.priority,
                    "enabled": job.enabled,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "next_run": job.next_run.isoformat() if job.next_run else None,
                    "running": job_id in self.running_jobs
                }
                for job_id, job in self.warming_jobs.items()
            },
            "recent_history": self.job_history[-10:]  # Last 10 jobs
        }


def create_cache_warming_manager(cache_manager, config: Optional[WarmingConfig] = None) -> CacheWarmingManager:
    """Create a cache warming manager with default or provided configuration."""
    if config is None:
        config = WarmingConfig()
    return CacheWarmingManager(cache_manager, config)