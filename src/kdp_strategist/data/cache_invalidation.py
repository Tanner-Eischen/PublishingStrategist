"""Cache invalidation policies for KDP Strategist.

This module implements intelligent cache invalidation strategies based on
data freshness requirements, dependencies, and business logic.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class InvalidationTrigger(Enum):
    """Types of invalidation triggers."""
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    DEPENDENCY_BASED = "dependency_based"
    MANUAL = "manual"
    CAPACITY_BASED = "capacity_based"
    DATA_FRESHNESS = "data_freshness"


class DataFreshnessLevel(Enum):
    """Data freshness requirements."""
    REAL_TIME = "real_time"  # < 1 minute
    NEAR_REAL_TIME = "near_real_time"  # < 5 minutes
    FRESH = "fresh"  # < 1 hour
    MODERATE = "moderate"  # < 6 hours
    STALE_OK = "stale_ok"  # < 24 hours
    ARCHIVAL = "archival"  # > 24 hours


@dataclass
class InvalidationRule:
    """Represents a cache invalidation rule."""
    rule_id: str
    trigger: InvalidationTrigger
    pattern: str  # Key pattern to match
    condition: Optional[Callable[[str, Any], bool]] = None
    freshness_level: DataFreshnessLevel = DataFreshnessLevel.MODERATE
    dependencies: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    priority: int = 5
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None


@dataclass
class InvalidationEvent:
    """Represents an invalidation event."""
    event_id: str
    trigger: InvalidationTrigger
    rule_id: str
    keys_invalidated: List[str]
    timestamp: datetime
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvalidationConfig:
    """Configuration for cache invalidation system."""
    enabled: bool = True
    check_interval_seconds: int = 60
    max_invalidations_per_batch: int = 1000
    rules_file: Path = Path("cache/invalidation_rules.json")
    event_history_limit: int = 10000
    enable_cascade_invalidation: bool = True
    enable_predictive_invalidation: bool = True


class CacheInvalidationManager:
    """Manages cache invalidation policies and execution."""
    
    def __init__(self, cache_manager, config: InvalidationConfig):
        self.cache_manager = cache_manager
        self.config = config
        self.rules: Dict[str, InvalidationRule] = {}
        self.event_history: List[InvalidationEvent] = []
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        # Background tasks
        self.invalidation_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_invalidations": 0,
            "time_based_invalidations": 0,
            "event_based_invalidations": 0,
            "dependency_invalidations": 0,
            "manual_invalidations": 0,
            "cascade_invalidations": 0,
        }
        
        # Initialize default rules
        self._initialize_default_rules()
        self._load_rules_from_file()
    
    def _initialize_default_rules(self) -> None:
        """Initialize default invalidation rules."""
        
        # Trend data invalidation - fresh data required
        self.rules["trends_freshness"] = InvalidationRule(
            rule_id="trends_freshness",
            trigger=InvalidationTrigger.TIME_BASED,
            pattern="trends:*",
            freshness_level=DataFreshnessLevel.FRESH,
            priority=1
        )
        
        # Competition data invalidation - moderate freshness
        self.rules["competition_freshness"] = InvalidationRule(
            rule_id="competition_freshness",
            trigger=InvalidationTrigger.TIME_BASED,
            pattern="competition:*",
            freshness_level=DataFreshnessLevel.MODERATE,
            priority=2
        )
        
        # Niche analysis invalidation - depends on trends and competition
        self.rules["niche_analysis_dependency"] = InvalidationRule(
            rule_id="niche_analysis_dependency",
            trigger=InvalidationTrigger.DEPENDENCY_BASED,
            pattern="niche_analysis:*",
            dependencies={"trends", "competition"},
            freshness_level=DataFreshnessLevel.MODERATE,
            priority=3
        )
        
        # API response cache - near real-time for critical APIs
        self.rules["api_response_freshness"] = InvalidationRule(
            rule_id="api_response_freshness",
            trigger=InvalidationTrigger.TIME_BASED,
            pattern="api_response:keepa:*",
            freshness_level=DataFreshnessLevel.NEAR_REAL_TIME,
            priority=1
        )
        
        # User session data - stale OK
        self.rules["session_cleanup"] = InvalidationRule(
            rule_id="session_cleanup",
            trigger=InvalidationTrigger.TIME_BASED,
            pattern="session:*",
            freshness_level=DataFreshnessLevel.STALE_OK,
            priority=4
        )
        
        # Temporary data - short TTL
        self.rules["temporary_cleanup"] = InvalidationRule(
            rule_id="temporary_cleanup",
            trigger=InvalidationTrigger.TIME_BASED,
            pattern="temp:*",
            freshness_level=DataFreshnessLevel.REAL_TIME,
            priority=5
        )
    
    async def start_invalidation_system(self) -> None:
        """Start the cache invalidation system."""
        if not self.config.enabled:
            logger.info("Cache invalidation system is disabled")
            return
        
        logger.info("Starting cache invalidation system")
        
        # Start background tasks
        self.invalidation_task = asyncio.create_task(self._invalidation_worker())
        self.monitoring_task = asyncio.create_task(self._monitoring_worker())
    
    async def stop_invalidation_system(self) -> None:
        """Stop the cache invalidation system."""
        logger.info("Stopping cache invalidation system")
        
        if self.invalidation_task:
            self.invalidation_task.cancel()
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        # Save rules to file
        self._save_rules_to_file()
    
    async def _invalidation_worker(self) -> None:
        """Background worker for cache invalidation."""
        while True:
            try:
                await self._check_invalidation_rules()
                await asyncio.sleep(self.config.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in invalidation worker: {e}")
                await asyncio.sleep(self.config.check_interval_seconds)
    
    async def _monitoring_worker(self) -> None:
        """Background worker for monitoring invalidation patterns."""
        while True:
            try:
                await self._analyze_invalidation_patterns()
                await asyncio.sleep(300)  # Analyze every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring worker: {e}")
                await asyncio.sleep(300)
    
    async def _check_invalidation_rules(self) -> None:
        """Check all invalidation rules and execute as needed."""
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            try:
                if rule.trigger == InvalidationTrigger.TIME_BASED:
                    await self._check_time_based_rule(rule)
                elif rule.trigger == InvalidationTrigger.DEPENDENCY_BASED:
                    await self._check_dependency_based_rule(rule)
                elif rule.trigger == InvalidationTrigger.DATA_FRESHNESS:
                    await self._check_freshness_based_rule(rule)
            except Exception as e:
                logger.error(f"Error checking invalidation rule {rule.rule_id}: {e}")
    
    async def _check_time_based_rule(self, rule: InvalidationRule) -> None:
        """Check and execute time-based invalidation rule."""
        max_age = self._get_max_age_for_freshness(rule.freshness_level)
        cutoff_time = datetime.now() - max_age
        
        # Get all cache entries matching the pattern
        matching_keys = await self._get_matching_keys(rule.pattern)
        keys_to_invalidate = []
        
        for key in matching_keys:
            # Check if entry exists and is old enough
            entry = getattr(self.cache_manager, 'entries', {}).get(key)
            if entry and entry.created_at < cutoff_time:
                keys_to_invalidate.append(key)
        
        if keys_to_invalidate:
            await self._execute_invalidation(rule, keys_to_invalidate, "Time-based expiration")
    
    async def _check_dependency_based_rule(self, rule: InvalidationRule) -> None:
        """Check and execute dependency-based invalidation rule."""
        # Check if any dependencies have been invalidated recently
        recent_invalidations = [
            event for event in self.event_history[-100:]  # Check last 100 events
            if event.timestamp > datetime.now() - timedelta(minutes=5)
        ]
        
        dependency_invalidated = False
        for event in recent_invalidations:
            for invalidated_key in event.keys_invalidated:
                for dependency in rule.dependencies:
                    if dependency in invalidated_key:
                        dependency_invalidated = True
                        break
                if dependency_invalidated:
                    break
            if dependency_invalidated:
                break
        
        if dependency_invalidated:
            matching_keys = await self._get_matching_keys(rule.pattern)
            if matching_keys:
                await self._execute_invalidation(
                    rule, 
                    matching_keys, 
                    "Dependency invalidation"
                )
    
    async def _check_freshness_based_rule(self, rule: InvalidationRule) -> None:
        """Check and execute freshness-based invalidation rule."""
        # This is similar to time-based but considers data access patterns
        matching_keys = await self._get_matching_keys(rule.pattern)
        keys_to_invalidate = []
        
        for key in matching_keys:
            if await self._should_invalidate_for_freshness(key, rule.freshness_level):
                keys_to_invalidate.append(key)
        
        if keys_to_invalidate:
            await self._execute_invalidation(
                rule, 
                keys_to_invalidate, 
                "Data freshness requirement"
            )
    
    async def _should_invalidate_for_freshness(self, key: str, freshness_level: DataFreshnessLevel) -> bool:
        """Determine if a key should be invalidated based on freshness requirements."""
        entry = getattr(self.cache_manager, 'entries', {}).get(key)
        if not entry:
            return False
        
        max_age = self._get_max_age_for_freshness(freshness_level)
        age = datetime.now() - entry.created_at
        
        # Consider access patterns for adaptive freshness
        if hasattr(entry, 'access_count') and entry.access_count > 10:
            # Frequently accessed data can be slightly staler
            max_age *= 1.5
        
        return age > max_age
    
    def _get_max_age_for_freshness(self, freshness_level: DataFreshnessLevel) -> timedelta:
        """Get maximum age for a given freshness level."""
        freshness_map = {
            DataFreshnessLevel.REAL_TIME: timedelta(minutes=1),
            DataFreshnessLevel.NEAR_REAL_TIME: timedelta(minutes=5),
            DataFreshnessLevel.FRESH: timedelta(hours=1),
            DataFreshnessLevel.MODERATE: timedelta(hours=6),
            DataFreshnessLevel.STALE_OK: timedelta(hours=24),
            DataFreshnessLevel.ARCHIVAL: timedelta(days=7),
        }
        return freshness_map.get(freshness_level, timedelta(hours=6))
    
    async def _get_matching_keys(self, pattern: str) -> List[str]:
        """Get cache keys matching the given pattern."""
        import fnmatch
        
        all_keys = list(getattr(self.cache_manager, 'entries', {}).keys())
        matching_keys = []
        
        for key in all_keys:
            if fnmatch.fnmatch(key, pattern):
                matching_keys.append(key)
        
        return matching_keys
    
    async def _execute_invalidation(self, rule: InvalidationRule, keys: List[str], reason: str) -> None:
        """Execute cache invalidation for the specified keys."""
        if not keys:
            return
        
        # Limit batch size
        keys_to_process = keys[:self.config.max_invalidations_per_batch]
        
        # Perform invalidation
        invalidated_keys = []
        for key in keys_to_process:
            try:
                success = await self.cache_manager.delete(key)
                if success:
                    invalidated_keys.append(key)
            except Exception as e:
                logger.error(f"Failed to invalidate key {key}: {e}")
        
        if invalidated_keys:
            # Update statistics
            self.stats["total_invalidations"] += len(invalidated_keys)
            if rule.trigger == InvalidationTrigger.TIME_BASED:
                self.stats["time_based_invalidations"] += len(invalidated_keys)
            elif rule.trigger == InvalidationTrigger.DEPENDENCY_BASED:
                self.stats["dependency_invalidations"] += len(invalidated_keys)
            
            # Record event
            event = InvalidationEvent(
                event_id=f"{rule.rule_id}_{datetime.now().timestamp()}",
                trigger=rule.trigger,
                rule_id=rule.rule_id,
                keys_invalidated=invalidated_keys,
                timestamp=datetime.now(),
                reason=reason
            )
            
            self.event_history.append(event)
            
            # Keep history within limits
            if len(self.event_history) > self.config.event_history_limit:
                self.event_history = self.event_history[-self.config.event_history_limit:]
            
            # Update rule last triggered time
            rule.last_triggered = datetime.now()
            
            # Perform cascade invalidation if enabled
            if self.config.enable_cascade_invalidation:
                await self._perform_cascade_invalidation(invalidated_keys)
            
            logger.info(f"Invalidated {len(invalidated_keys)} keys for rule {rule.rule_id}: {reason}")
    
    async def _perform_cascade_invalidation(self, invalidated_keys: List[str]) -> None:
        """Perform cascade invalidation based on dependencies."""
        cascade_keys = set()
        
        for key in invalidated_keys:
            # Find dependent keys
            for dependent_key, dependencies in self.dependency_graph.items():
                if any(dep in key for dep in dependencies):
                    cascade_keys.add(dependent_key)
        
        if cascade_keys:
            cascade_keys_list = list(cascade_keys)
            for key in cascade_keys_list:
                try:
                    await self.cache_manager.delete(key)
                    self.stats["cascade_invalidations"] += 1
                except Exception as e:
                    logger.error(f"Failed to cascade invalidate key {key}: {e}")
            
            logger.info(f"Cascade invalidated {len(cascade_keys_list)} additional keys")
    
    async def _analyze_invalidation_patterns(self) -> None:
        """Analyze invalidation patterns for optimization."""
        if len(self.event_history) < 10:
            return
        
        # Analyze recent invalidation frequency
        recent_events = [
            event for event in self.event_history
            if event.timestamp > datetime.now() - timedelta(hours=1)
        ]
        
        if len(recent_events) > 100:  # High invalidation rate
            logger.warning(f"High invalidation rate detected: {len(recent_events)} invalidations in the last hour")
            
            # Suggest optimizations
            await self._suggest_invalidation_optimizations(recent_events)
    
    async def _suggest_invalidation_optimizations(self, recent_events: List[InvalidationEvent]) -> None:
        """Suggest optimizations based on invalidation patterns."""
        # Analyze most frequently invalidated patterns
        pattern_counts = {}
        for event in recent_events:
            for key in event.keys_invalidated:
                pattern = key.split(':')[0] if ':' in key else key
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        # Find patterns with high invalidation rates
        high_invalidation_patterns = [
            pattern for pattern, count in pattern_counts.items()
            if count > 20  # More than 20 invalidations in an hour
        ]
        
        if high_invalidation_patterns:
            logger.info(f"High invalidation patterns detected: {high_invalidation_patterns}")
            logger.info("Consider adjusting TTL or caching strategy for these patterns")
    
    async def add_invalidation_rule(self, rule: InvalidationRule) -> None:
        """Add a new invalidation rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added invalidation rule: {rule.rule_id}")
    
    async def remove_invalidation_rule(self, rule_id: str) -> bool:
        """Remove an invalidation rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed invalidation rule: {rule_id}")
            return True
        return False
    
    async def trigger_manual_invalidation(self, pattern: str, reason: str = "Manual trigger") -> int:
        """Manually trigger invalidation for keys matching a pattern."""
        matching_keys = await self._get_matching_keys(pattern)
        
        if matching_keys:
            # Create temporary rule for manual invalidation
            temp_rule = InvalidationRule(
                rule_id=f"manual_{datetime.now().timestamp()}",
                trigger=InvalidationTrigger.MANUAL,
                pattern=pattern
            )
            
            await self._execute_invalidation(temp_rule, matching_keys, reason)
            self.stats["manual_invalidations"] += len(matching_keys)
            
            return len(matching_keys)
        
        return 0
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        return await self.cache_manager.invalidate_by_tag(tag)
    
    async def invalidate_by_dependency(self, dependency: str) -> int:
        """Invalidate all entries that depend on a specific dependency."""
        return await self.cache_manager.invalidate_by_dependency(dependency)
    
    def add_dependency(self, key: str, dependencies: Set[str]) -> None:
        """Add dependency relationship for cascade invalidation."""
        self.dependency_graph[key] = dependencies
    
    def remove_dependency(self, key: str) -> None:
        """Remove dependency relationship."""
        if key in self.dependency_graph:
            del self.dependency_graph[key]
    
    def _load_rules_from_file(self) -> None:
        """Load invalidation rules from file."""
        if not self.config.rules_file.exists():
            return
        
        try:
            with open(self.config.rules_file, 'r') as f:
                rules_data = json.load(f)
            
            for rule_id, rule_config in rules_data.items():
                if rule_id not in self.rules:  # Don't override default rules
                    rule = InvalidationRule(
                        rule_id=rule_id,
                        trigger=InvalidationTrigger(rule_config['trigger']),
                        pattern=rule_config['pattern'],
                        freshness_level=DataFreshnessLevel(rule_config.get('freshness_level', 'moderate')),
                        dependencies=set(rule_config.get('dependencies', [])),
                        tags=set(rule_config.get('tags', [])),
                        priority=rule_config.get('priority', 5),
                        enabled=rule_config.get('enabled', True)
                    )
                    self.rules[rule_id] = rule
            
            logger.info(f"Loaded {len(rules_data)} invalidation rules from file")
        except Exception as e:
            logger.error(f"Failed to load invalidation rules: {e}")
    
    def _save_rules_to_file(self) -> None:
        """Save invalidation rules to file."""
        try:
            self.config.rules_file.parent.mkdir(parents=True, exist_ok=True)
            
            rules_data = {}
            for rule_id, rule in self.rules.items():
                rules_data[rule_id] = {
                    'trigger': rule.trigger.value,
                    'pattern': rule.pattern,
                    'freshness_level': rule.freshness_level.value,
                    'dependencies': list(rule.dependencies),
                    'tags': list(rule.tags),
                    'priority': rule.priority,
                    'enabled': rule.enabled,
                    'created_at': rule.created_at.isoformat(),
                    'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None
                }
            
            with open(self.config.rules_file, 'w') as f:
                json.dump(rules_data, f, indent=2)
            
            logger.info(f"Saved {len(rules_data)} invalidation rules to file")
        except Exception as e:
            logger.error(f"Failed to save invalidation rules: {e}")
    
    def get_invalidation_status(self) -> Dict[str, Any]:
        """Get current invalidation system status."""
        return {
            "enabled": self.config.enabled,
            "total_rules": len(self.rules),
            "active_rules": len([r for r in self.rules.values() if r.enabled]),
            "statistics": self.stats,
            "recent_events": [
                {
                    "event_id": event.event_id,
                    "trigger": event.trigger.value,
                    "rule_id": event.rule_id,
                    "keys_count": len(event.keys_invalidated),
                    "timestamp": event.timestamp.isoformat(),
                    "reason": event.reason
                }
                for event in self.event_history[-10:]
            ],
            "rules_status": {
                rule_id: {
                    "trigger": rule.trigger.value,
                    "pattern": rule.pattern,
                    "enabled": rule.enabled,
                    "priority": rule.priority,
                    "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None
                }
                for rule_id, rule in self.rules.items()
            }
        }


def create_cache_invalidation_manager(cache_manager, config: Optional[InvalidationConfig] = None) -> CacheInvalidationManager:
    """Create a cache invalidation manager with default or provided configuration."""
    if config is None:
        config = InvalidationConfig()
    return CacheInvalidationManager(cache_manager, config)