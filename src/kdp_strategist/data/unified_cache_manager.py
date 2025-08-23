# -*- coding: utf-8 -*-
"""Unified cache management system for KDP Strategist.

This module consolidates functionality from cache_manager.py and intelligent_cache.py
into a single, comprehensive cache management system with:
- Multi-tier caching (memory, file, Redis)
- Intelligent caching strategies (LRU, LFU, adaptive)
- Advanced analytics and monitoring
- Connection pooling and performance optimizations
- Cache warming and invalidation
"""

import asyncio
import json
import logging
import time
import hashlib
import pickle
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, Set, List, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Try to import Redis, but make it optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.info("Redis not available - Redis caching will be disabled")


class CacheDataType(Enum):
    """Types of data that can be cached with different strategies."""
    TREND_DATA = "trend_data"
    COMPETITION_DATA = "competition_data"
    NICHE_ANALYSIS = "niche_analysis"
    API_RESPONSE = "api_response"
    USER_SESSION = "user_session"
    TEMPORARY = "temporary"


class CacheStrategy(Enum):
    """Different caching strategies for various data types."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on access patterns
    WRITE_THROUGH = "write_through"  # Write through to persistent storage
    WRITE_BACK = "write_back"  # Write back to persistent storage


class CachePriority(Enum):
    """Cache priority levels for different data types."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class CacheEntry:
    """Enhanced cache entry with comprehensive metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl: Optional[int]
    priority: CachePriority
    tags: Set[str]
    dependencies: Set[str]
    size_bytes: int
    compressed: bool = False
    tier: str = "memory"
    
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        if not self.ttl:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    def update_access(self) -> None:
        """Update access statistics."""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class UnifiedCacheConfig:
    """Comprehensive configuration for unified cache management."""
    # Cache type configuration
    cache_type: str = "multi-tier"  # "memory", "file", "redis", "multi-tier"
    cache_dir: Path = Path("cache")
    
    # Redis configuration
    redis_url: Optional[str] = None
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_socket_timeout: float = 5.0
    redis_connection_pool_size: int = 10
    
    # TTL configurations by data type
    default_ttl: int = 3600
    ttl_by_data_type: Dict[str, Optional[int]] = field(default_factory=lambda: {
        "trend_data": 7200,      # 2 hours for trend data
        "competition_data": 3600, # 1 hour for competition data
        "niche_analysis": 14400,  # 4 hours for niche analysis
        "api_response": 1800,     # 30 minutes for API responses
        "user_session": 86400,    # 24 hours for user sessions
        "temporary": None         # No TTL for temporary data by default
    })
    
    # Multi-tier cache configuration
    memory_cache_size: int = 500
    file_cache_size: int = 5000
    redis_cache_size: int = 50000
    tier_promotion_threshold: int = 3  # Access count to promote to higher tier
    
    # Memory and size limits
    max_cache_size: int = 1000
    max_memory_mb: int = 500
    max_entries: int = 10000
    
    # Cleanup and maintenance
    cleanup_interval: int = 86400
    auto_cleanup_enabled: bool = True
    stale_data_threshold_hours: int = 24
    health_check_interval: int = 300  # 5 minutes
    
    # Compression and serialization
    compression: bool = True
    compression_threshold: int = 1024  # Compress entries larger than 1KB
    serialization: str = "json"
    
    # Batch operation settings
    batch_size_limit: int = 100
    batch_timeout_seconds: float = 30.0
    enable_batch_compression: bool = True
    
    # Intelligent caching features
    enable_persistence: bool = True
    persistence_path: Path = Path("cache/unified_cache.db")
    cache_warming_enabled: bool = True
    adaptive_ttl_enabled: bool = True
    hit_rate_target: float = 0.85
    
    # Environment-specific configurations
    environment: str = "development"  # development, testing, production
    enable_monitoring: bool = True
    enable_alerting: bool = False
    alert_threshold_hit_rate: float = 0.3  # Alert if hit rate drops below 30%
    alert_threshold_memory_mb: int = 80  # Alert if memory usage exceeds 80MB
    
    @classmethod
    def for_environment(cls, env: str) -> 'UnifiedCacheConfig':
        """Create environment-specific cache configuration."""
        if env == "production":
            return cls(
                cache_type="redis",
                max_cache_size=10000,
                max_memory_mb=500,
                cleanup_interval=3600,  # 1 hour
                health_check_interval=60,  # 1 minute
                enable_monitoring=True,
                enable_alerting=True,
                environment="production"
            )
        elif env == "testing":
            return cls(
                cache_type="memory",
                max_cache_size=100,
                max_memory_mb=10,
                cleanup_interval=300,  # 5 minutes
                health_check_interval=30,  # 30 seconds
                enable_monitoring=False,
                enable_alerting=False,
                environment="testing"
            )
        else:  # development
            return cls(
                cache_type="file",
                max_cache_size=1000,
                max_memory_mb=50,
                cleanup_interval=1800,  # 30 minutes
                health_check_interval=300,  # 5 minutes
                enable_monitoring=True,
                enable_alerting=False,
                environment="development"
            )


class RedisCacheTier:
    """Redis cache tier implementation with connection pooling."""
    
    def __init__(self, config: UnifiedCacheConfig):
        self.config = config
        self.redis_client = None
        self._connection_pool = None
        
        if REDIS_AVAILABLE and config.redis_url:
            try:
                self._connection_pool = redis.ConnectionPool.from_url(
                    config.redis_url,
                    db=config.redis_db,
                    password=config.redis_password,
                    socket_timeout=config.redis_socket_timeout,
                    max_connections=config.redis_connection_pool_size
                )
                self.redis_client = redis.Redis(connection_pool=self._connection_pool)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache tier initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
                self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self.redis_client:
            return None
        
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        if not self.redis_client:
            return False
        
        try:
            data = json.dumps(value, default=str)
            if ttl:
                return self.redis_client.setex(key, ttl, data)
            else:
                return self.redis_client.set(key, data)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from Redis cache."""
        if not self.redis_client or not keys:
            return {}
        
        try:
            pipe = self.redis_client.pipeline()
            for key in keys:
                pipe.get(key)
            results = pipe.execute()
            
            batch_results = {}
            for key, result in zip(keys, results):
                if result:
                    try:
                        batch_results[key] = json.loads(result.decode('utf-8'))
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode Redis value for key {key}")
            
            return batch_results
        except Exception as e:
            logger.error(f"Redis batch get error: {e}")
            return {}
    
    def set_batch(self, items: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """Set multiple values in Redis cache."""
        if not self.redis_client or not items:
            return 0
        
        try:
            pipe = self.redis_client.pipeline()
            for key, value in items.items():
                data = json.dumps(value, default=str)
                if ttl:
                    pipe.setex(key, ttl, data)
                else:
                    pipe.set(key, data)
            
            results = pipe.execute()
            return sum(1 for result in results if result)
        except Exception as e:
            logger.error(f"Redis batch set error: {e}")
            return 0
    
    def clear(self) -> bool:
        """Clear all Redis cache entries (use with caution)."""
        if not self.redis_client:
            return False
        
        try:
            return self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis cache information."""
        if not self.redis_client:
            return {"available": False}
        
        try:
            info = self.redis_client.info()
            return {
                "available": True,
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.error(f"Redis info error: {e}")
            return {"available": False, "error": str(e)}


class UnifiedCacheManager:
    """Unified cache manager combining multi-tier caching with intelligent strategies."""
    
    def __init__(self, config: UnifiedCacheConfig):
        self.config = config
        self._lock = threading.RLock()
        
        # Cache storage
        self.entries: Dict[str, CacheEntry] = {}
        self.access_order: deque = deque()  # For LRU
        self.frequency_counter: Dict[str, int] = defaultdict(int)  # For LFU
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        self.dependency_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Multi-tier cache tiers
        self.cache_tiers = {}
        self._init_cache_tiers()
        
        # Enhanced statistics tracking
        self.stats = {
            "hits": 0, 
            "misses": 0, 
            "sets": 0, 
            "deletes": 0,
            "evictions": 0,
            "compressions": 0,
            "decompressions": 0,
            "total_access_time": 0.0,
            "access_count": 0,
            "hit_times": [],
            "miss_times": [],
            "tier_hits": defaultdict(int),
            "tier_misses": defaultdict(int),
            "data_type_stats": defaultdict(lambda: {
                "hits": 0, "misses": 0, "sets": 0, "avg_size": 0
            })
        }
        
        # Access pattern tracking for intelligent caching
        self.access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.ttl_adjustments: Dict[str, int] = {}
        
        # Cache warming
        self.warming_queue: asyncio.Queue = asyncio.Queue()
        self.warming_callbacks: List[Callable[[], Dict[str, Any]]] = []
        
        # Performance monitoring
        self.performance_history: deque = deque(maxlen=1000)
        self.hit_rate_history: deque = deque(maxlen=100)
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.warming_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Initialize
        self._initialize()
    
    def _init_cache_tiers(self):
        """Initialize cache tiers based on configuration."""
        if self.config.cache_type in ["redis", "multi-tier"]:
            self.cache_tiers["redis"] = RedisCacheTier(self.config)
        
        # Memory and file tiers are always available for multi-tier
        if self.config.cache_type in ["memory", "file", "multi-tier"]:
            self.cache_tiers["memory"] = self  # Self-reference for memory tier
            if self.config.cache_type in ["file", "multi-tier"]:
                # File tier implementation would go here
                pass
    
    def _initialize(self) -> None:
        """Initialize the cache manager."""
        if self.config.enable_persistence:
            self._load_from_persistence()
        
        # Start background tasks
        if asyncio.get_event_loop().is_running():
            asyncio.create_task(self._start_background_tasks())
    
    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        if self.config.cache_warming_enabled:
            self.warming_task = asyncio.create_task(self._warming_worker())
        
        self.monitoring_task = asyncio.create_task(self._monitoring_worker())
    
    def get(self, key: str, data_type: CacheDataType = CacheDataType.TEMPORARY, default: Any = None) -> Any:
        """Get value from cache with intelligent tier selection."""
        start_time = time.time()
        
        with self._lock:
            # Try to get from appropriate tier order
            tier_order = self._get_tier_order()
            
            for tier_name in tier_order:
                value = self._get_from_tier(key, tier_name)
                if value is not None:
                    self._record_cache_hit(start_time, tier_name)
                    self._update_access_pattern(key, data_type)
                    
                    # Promote to higher tier if accessed frequently
                    if tier_name != tier_order[0]:  # Not already in highest tier
                        self._promote_to_higher_tier(key, value, tier_name, data_type)
                    
                    return value
            
            # Cache miss
            self._record_cache_miss(start_time, "not_found")
            return default
    
    def set(self, 
            key: str, 
            value: Any, 
            ttl: Optional[int] = None,
            data_type: CacheDataType = CacheDataType.TEMPORARY,
            priority: CachePriority = CachePriority.MEDIUM,
            tags: Optional[Set[str]] = None,
            dependencies: Optional[Set[str]] = None,
            strategy: CacheStrategy = CacheStrategy.ADAPTIVE) -> bool:
        """Set value in cache with intelligent tier placement."""
        with self._lock:
            # Calculate adaptive TTL if enabled
            if self.config.adaptive_ttl_enabled and ttl is None:
                ttl = self._calculate_adaptive_ttl(key, data_type)
            elif ttl is None:
                ttl = self._get_ttl_for_data_type(data_type)
            
            # Determine optimal tier for storage
            optimal_tier = self._determine_optimal_tier(key, value, data_type)
            
            # Create cache entry
            entry = self._create_cache_entry(
                key, value, ttl, priority, tags, dependencies, optimal_tier
            )
            
            # Check if we need to evict entries
            if self._should_evict():
                self._evict_entries(strategy)
            
            # Store in memory index
            self.entries[key] = entry
            self._update_indexes(key, entry)
            self._update_access_order(key)
            
            # Store in appropriate tier
            success = self._set_in_tier(key, value, optimal_tier, ttl)
            
            if success:
                self.stats["sets"] += 1
                self.stats["data_type_stats"][data_type.value]["sets"] += 1
            
            return success
    
    def delete(self, key: str) -> bool:
        """Delete entry from all cache tiers."""
        with self._lock:
            success = False
            
            # Remove from memory index
            if key in self.entries:
                entry = self.entries[key]
                self._remove_entry(key)
                success = True
            
            # Remove from all tiers
            for tier_name in self.cache_tiers.keys():
                if self._delete_from_tier(key, tier_name):
                    success = True
            
            if success:
                self.stats["deletes"] += 1
            
            return success
    
    def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache efficiently."""
        results = {}
        remaining_keys = list(keys)
        
        # Try each tier in order
        for tier_name in self._get_tier_order():
            if not remaining_keys:
                break
            
            tier_results = self._get_batch_from_tier(remaining_keys, tier_name)
            results.update(tier_results)
            
            # Remove found keys from remaining
            remaining_keys = [k for k in remaining_keys if k not in tier_results]
        
        return results
    
    def set_batch(self, items: Dict[str, Any], ttl: Optional[int] = None,
                  data_type: CacheDataType = CacheDataType.TEMPORARY) -> int:
        """Set multiple values in cache efficiently."""
        success_count = 0
        
        for key, value in items.items():
            if self.set(key, value, ttl, data_type):
                success_count += 1
        
        return success_count
    
    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with the specified tag."""
        with self._lock:
            keys_to_remove = self.tag_index.get(tag, set()).copy()
            for key in keys_to_remove:
                self.delete(key)
            return len(keys_to_remove)
    
    def invalidate_by_dependency(self, dependency: str) -> int:
        """Invalidate all entries that depend on the specified dependency."""
        with self._lock:
            keys_to_remove = self.dependency_index.get(dependency, set()).copy()
            for key in keys_to_remove:
                self.delete(key)
            return len(keys_to_remove)
    
    def exists(self, key: str) -> bool:
        """Check if key exists in any cache tier."""
        return key in self.entries or any(
            tier.exists(key) if hasattr(tier, 'exists') else False
            for tier in self.cache_tiers.values()
        )
    
    def clear(self) -> bool:
        """Clear all cache entries from all tiers."""
        with self._lock:
            # Clear memory structures
            self.entries.clear()
            self.access_order.clear()
            self.frequency_counter.clear()
            self.tag_index.clear()
            self.dependency_index.clear()
            
            # Clear all tiers
            success = True
            for tier in self.cache_tiers.values():
                if hasattr(tier, 'clear') and tier != self:
                    if not tier.clear():
                        success = False
            
            return success
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries from all tiers."""
        with self._lock:
            expired_keys = []
            current_time = datetime.now()
            
            for key, entry in self.entries.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.delete(key)
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "total_entries": len(self.entries),
            "memory_usage_mb": self._calculate_memory_usage() / (1024 * 1024),
            "tier_stats": {
                tier_name: {
                    "hits": self.stats["tier_hits"][tier_name],
                    "misses": self.stats["tier_misses"][tier_name]
                }
                for tier_name in self.cache_tiers.keys()
            },
            "data_type_stats": dict(self.stats["data_type_stats"]),
            "evictions": self.stats["evictions"],
            "compressions": self.stats["compressions"],
            "decompressions": self.stats["decompressions"]
        }
    
    # Helper methods
    def _get_tier_order(self) -> List[str]:
        """Get the order of tiers to check for cache hits."""
        if self.config.cache_type == "multi-tier":
            return ["memory", "file", "redis"]
        elif self.config.cache_type == "redis":
            return ["redis"]
        elif self.config.cache_type == "file":
            return ["file"]
        else:  # memory
            return ["memory"]
    
    def _get_from_tier(self, key: str, tier_name: str) -> Optional[Any]:
        """Get value from specific tier."""
        if tier_name == "memory":
            if key in self.entries:
                entry = self.entries[key]
                if not entry.is_expired():
                    entry.update_access()
                    return self._deserialize_value(entry.value, entry.compressed)
                else:
                    self._remove_entry(key)
            return None
        
        tier = self.cache_tiers.get(tier_name)
        if tier and hasattr(tier, 'get'):
            return tier.get(key)
        
        return None
    
    def _set_in_tier(self, key: str, value: Any, tier_name: str, ttl: Optional[int] = None) -> bool:
        """Set value in specific tier."""
        if tier_name == "memory":
            return True  # Already handled in main set method
        
        tier = self.cache_tiers.get(tier_name)
        if tier and hasattr(tier, 'set'):
            return tier.set(key, value, ttl)
        
        return False
    
    def _delete_from_tier(self, key: str, tier_name: str) -> bool:
        """Delete value from specific tier."""
        if tier_name == "memory":
            return True  # Already handled in main delete method
        
        tier = self.cache_tiers.get(tier_name)
        if tier and hasattr(tier, 'delete'):
            return tier.delete(key)
        
        return False
    
    def _get_batch_from_tier(self, keys: List[str], tier_name: str) -> Dict[str, Any]:
        """Get multiple values from specific tier."""
        if tier_name == "memory":
            results = {}
            for key in keys:
                value = self._get_from_tier(key, "memory")
                if value is not None:
                    results[key] = value
            return results
        
        tier = self.cache_tiers.get(tier_name)
        if tier and hasattr(tier, 'get_batch'):
            return tier.get_batch(keys)
        
        return {}
    
    def _record_cache_hit(self, start_time: float, tier: str):
        """Record cache hit statistics."""
        response_time = time.time() - start_time
        self.stats["hits"] += 1
        self.stats["tier_hits"][tier] += 1
        self.stats["hit_times"].append(response_time)
        self.stats["total_access_time"] += response_time
        self.stats["access_count"] += 1
        
        # Keep only recent times for performance
        if len(self.stats["hit_times"]) > 1000:
            self.stats["hit_times"] = self.stats["hit_times"][-500:]
    
    def _record_cache_miss(self, start_time: float, reason: str):
        """Record cache miss statistics."""
        response_time = time.time() - start_time
        self.stats["misses"] += 1
        self.stats["miss_times"].append(response_time)
        self.stats["total_access_time"] += response_time
        self.stats["access_count"] += 1
        
        # Keep only recent times for performance
        if len(self.stats["miss_times"]) > 1000:
            self.stats["miss_times"] = self.stats["miss_times"][-500:]
    
    def _update_access_pattern(self, key: str, data_type: CacheDataType):
        """Update access pattern for intelligent caching."""
        self.access_patterns[key].append(datetime.now())
        self.frequency_counter[key] += 1
        
        # Keep only recent access patterns
        if len(self.access_patterns[key]) > 100:
            self.access_patterns[key] = self.access_patterns[key][-50:]
    
    def _promote_to_higher_tier(self, key: str, value: Any, current_tier: str, data_type: CacheDataType):
        """Promote frequently accessed items to higher tiers."""
        if self.frequency_counter[key] >= self.config.tier_promotion_threshold:
            tier_order = self._get_tier_order()
            current_index = tier_order.index(current_tier) if current_tier in tier_order else -1
            
            if current_index > 0:  # Can promote to higher tier
                higher_tier = tier_order[current_index - 1]
                if self._has_tier_capacity(higher_tier):
                    ttl = self._get_ttl_for_data_type(data_type)
                    self._set_in_tier(key, value, higher_tier, ttl)
                    
                    # Update entry tier
                    if key in self.entries:
                        self.entries[key].tier = higher_tier
    
    def _has_tier_capacity(self, tier_name: str) -> bool:
        """Check if tier has capacity for new entries."""
        if tier_name == "memory":
            return len(self.entries) < self.config.memory_cache_size
        # Add capacity checks for other tiers as needed
        return True
    
    def _get_ttl_for_data_type(self, data_type: CacheDataType) -> Optional[int]:
        """Get TTL for specific data type."""
        return self.config.ttl_by_data_type.get(data_type.value, self.config.default_ttl)
    
    def _determine_optimal_tier(self, key: str, value: Any, data_type: CacheDataType) -> str:
        """Determine optimal tier for storing data."""
        # Simple heuristic: high priority and frequently accessed data goes to memory
        if data_type in [CacheDataType.USER_SESSION, CacheDataType.API_RESPONSE]:
            return "memory"
        elif data_type in [CacheDataType.TREND_DATA, CacheDataType.COMPETITION_DATA]:
            return "file" if "file" in self.cache_tiers else "memory"
        else:
            return "redis" if "redis" in self.cache_tiers else "memory"
    
    def _calculate_adaptive_ttl(self, key: str, data_type: CacheDataType) -> int:
        """Calculate adaptive TTL based on access patterns."""
        base_ttl = self._get_ttl_for_data_type(data_type) or self.config.default_ttl
        
        # Adjust based on access frequency
        if key in self.access_patterns:
            recent_accesses = [
                access for access in self.access_patterns[key]
                if access > datetime.now() - timedelta(hours=24)
            ]
            
            if len(recent_accesses) > 10:  # Frequently accessed
                return int(base_ttl * 1.5)  # Increase TTL
            elif len(recent_accesses) < 2:  # Rarely accessed
                return int(base_ttl * 0.5)  # Decrease TTL
        
        return base_ttl
    
    def _create_cache_entry(self, key: str, value: Any, ttl: Optional[int], 
                           priority: CachePriority, tags: Optional[Set[str]], 
                           dependencies: Optional[Set[str]], tier: str) -> CacheEntry:
        """Create a cache entry with proper serialization and compression."""
        # Serialize value
        serialized_value = self._serialize_value(value)
        size_bytes = len(serialized_value) if isinstance(serialized_value, bytes) else len(str(serialized_value))
        compressed = False
        
        # Compress if needed
        if self.config.compression and size_bytes > self.config.compression_threshold:
            serialized_value = self._compress_value(serialized_value)
            compressed = True
            self.stats["compressions"] += 1
        
        return CacheEntry(
            key=key,
            value=serialized_value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            ttl=ttl,
            priority=priority,
            tags=tags or set(),
            dependencies=dependencies or set(),
            size_bytes=size_bytes,
            compressed=compressed,
            tier=tier
        )
    
    def _serialize_value(self, value: Any) -> Union[str, bytes]:
        """Serialize value for storage."""
        if self.config.serialization == "pickle":
            return pickle.dumps(value)
        else:  # json
            return json.dumps(value, default=str)
    
    def _deserialize_value(self, value: Union[str, bytes], compressed: bool = False) -> Any:
        """Deserialize value from storage."""
        if compressed:
            value = self._decompress_value(value)
            self.stats["decompressions"] += 1
        
        if self.config.serialization == "pickle":
            return pickle.loads(value)
        else:  # json
            return json.loads(value)
    
    def _compress_value(self, value: Union[str, bytes]) -> bytes:
        """Compress value using gzip."""
        if isinstance(value, str):
            value = value.encode('utf-8')
        return gzip.compress(value)
    
    def _decompress_value(self, value: bytes) -> Union[str, bytes]:
        """Decompress value using gzip."""
        decompressed = gzip.decompress(value)
        if self.config.serialization == "json":
            return decompressed.decode('utf-8')
        return decompressed
    
    def _should_evict(self) -> bool:
        """Check if cache eviction is needed."""
        current_memory = self._calculate_memory_usage()
        return (len(self.entries) >= self.config.max_entries or 
                current_memory >= self.config.max_memory_mb * 1024 * 1024)
    
    def _evict_entries(self, strategy: CacheStrategy) -> None:
        """Evict entries based on the specified strategy."""
        if strategy == CacheStrategy.LRU:
            self._evict_lru()
        elif strategy == CacheStrategy.LFU:
            self._evict_lfu()
        elif strategy == CacheStrategy.ADAPTIVE:
            self._evict_adaptive()
        else:
            self._evict_lru()  # Default to LRU
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        while self._should_evict() and self.access_order:
            key = self.access_order.popleft()
            if key in self.entries:
                self._remove_entry(key)
                self.stats["evictions"] += 1
    
    def _evict_lfu(self) -> None:
        """Evict least frequently used entries."""
        if not self.entries:
            return
        
        # Sort by access count and priority
        sorted_entries = sorted(
            self.entries.items(),
            key=lambda x: (x[1].access_count, x[1].priority.value)
        )
        
        # Evict lowest frequency entries
        evict_count = max(1, len(self.entries) // 10)  # Evict 10% of entries
        for key, _ in sorted_entries[:evict_count]:
            if self._should_evict():
                self._remove_entry(key)
                self.stats["evictions"] += 1
            else:
                break
    
    def _evict_adaptive(self) -> None:
        """Evict entries using adaptive strategy."""
        # Combine LRU and LFU strategies
        if not self.entries:
            return
        
        # Score entries based on recency, frequency, and priority
        scored_entries = []
        current_time = datetime.now()
        
        for key, entry in self.entries.items():
            recency_score = (current_time - entry.last_accessed).total_seconds()
            frequency_score = 1.0 / (entry.access_count + 1)
            priority_score = 1.0 / entry.priority.value
            
            # Higher score = more likely to be evicted
            total_score = recency_score * frequency_score * priority_score
            scored_entries.append((key, total_score))
        
        # Sort by score (highest first)
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        
        # Evict highest scoring entries
        evict_count = max(1, len(self.entries) // 10)  # Evict 10% of entries
        for key, _ in scored_entries[:evict_count]:
            if self._should_evict():
                self._remove_entry(key)
                self.stats["evictions"] += 1
            else:
                break
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry from all internal structures."""
        if key in self.entries:
            entry = self.entries[key]
            
            # Remove from indexes
            for tag in entry.tags:
                self.tag_index[tag].discard(key)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]
            
            for dependency in entry.dependencies:
                self.dependency_index[dependency].discard(key)
                if not self.dependency_index[dependency]:
                    del self.dependency_index[dependency]
            
            # Remove from access tracking
            if key in self.access_order:
                self.access_order.remove(key)
            
            if key in self.frequency_counter:
                del self.frequency_counter[key]
            
            if key in self.access_patterns:
                del self.access_patterns[key]
            
            # Remove entry
            del self.entries[key]
    
    def _update_indexes(self, key: str, entry: CacheEntry) -> None:
        """Update tag and dependency indexes."""
        for tag in entry.tags:
            self.tag_index[tag].add(key)
        
        for dependency in entry.dependencies:
            self.dependency_index[dependency].add(key)
    
    def _update_access_order(self, key: str) -> None:
        """Update access order for LRU tracking."""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def _calculate_memory_usage(self) -> int:
        """Calculate approximate memory usage in bytes."""
        total_size = 0
        for entry in self.entries.values():
            total_size += entry.size_bytes
        return total_size
    
    def _load_from_persistence(self) -> None:
        """Load cache from persistent storage."""
        # Implementation for loading from persistence
        # This would read from the configured persistence path
        pass
    
    async def _cleanup_worker(self) -> None:
        """Background worker for cache cleanup."""
        while True:
            try:
                self.cleanup_expired()
                await asyncio.sleep(self.config.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _warming_worker(self) -> None:
        """Background worker for cache warming."""
        while True:
            try:
                # Process warming queue
                if not self.warming_queue.empty():
                    warming_data = await self.warming_queue.get()
                    # Process warming data
                    pass
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in warming worker: {e}")
                await asyncio.sleep(60)
    
    async def _monitoring_worker(self) -> None:
        """Background worker for performance monitoring."""
        while True:
            try:
                # Collect performance metrics
                stats = self.get_stats()
                self.performance_history.append({
                    "timestamp": datetime.now(),
                    "stats": stats
                })
                
                # Update hit rate history
                self.hit_rate_history.append(stats["hit_rate"])
                
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring worker: {e}")
                await asyncio.sleep(60)


# Factory function for easy instantiation
def create_unified_cache_manager(environment: str = "development", **kwargs) -> UnifiedCacheManager:
    """Create a unified cache manager with environment-specific configuration."""
    config = UnifiedCacheConfig.for_environment(environment)
    
    # Override with any provided kwargs
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return UnifiedCacheManager(config)


# Default instance for backward compatibility
default_cache_manager = None

def get_default_cache_manager() -> UnifiedCacheManager:
    """Get the default cache manager instance."""
    global default_cache_manager
    if default_cache_manager is None:
        default_cache_manager = create_unified_cache_manager()
    return default_cache_manager