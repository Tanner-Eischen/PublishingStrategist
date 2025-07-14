"""Cache management system for KDP Strategist.

Provides flexible caching with support for:
- File-based caching for development
- Redis caching for production
- Memory caching for temporary data
- TTL (Time To Live) management
- Cache invalidation and cleanup
"""

import json
import pickle
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, Union, List
from dataclasses import dataclass

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for cache management."""
    cache_type: str = "file"  # "file", "redis", "memory"
    cache_dir: Path = Path("cache")
    redis_url: Optional[str] = None
    default_ttl: int = 3600  # seconds (1 hour)
    max_cache_size: int = 1000  # max items in memory cache
    cleanup_interval: int = 86400  # seconds (24 hours)
    compression: bool = True
    serialization: str = "json"  # "json", "pickle"


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend for temporary storage."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.access_times: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if self._is_expired(entry):
            self.delete(key)
            return None
        
        # Update access time for LRU
        self.access_times[key] = datetime.now()
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        try:
            # Evict if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            expires_at = None
            if ttl is not None:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            
            self.cache[key] = {
                "value": value,
                "created_at": datetime.now(),
                "expires_at": expires_at,
            }
            self.access_times[key] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        if key in self.cache:
            del self.cache[key]
            self.access_times.pop(key, None)
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        if key not in self.cache:
            return False
        
        if self._is_expired(self.cache[key]):
            self.delete(key)
            return False
        
        return True
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        self.cache.clear()
        self.access_times.clear()
        return True
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        expired_keys = []
        for key, entry in self.cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            self.delete(key)
        
        return len(expired_keys)
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        expires_at = entry.get("expires_at")
        return expires_at is not None and datetime.now() > expires_at
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self.delete(lru_key)


class FileCacheBackend(CacheBackend):
    """File-based cache backend for persistent storage."""
    
    def __init__(self, cache_dir: Path, serialization: str = "json", compression: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.serialization = serialization
        self.compression = compression
        
        # Create metadata directory
        self.meta_dir = self.cache_dir / "metadata"
        self.meta_dir.mkdir(exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from file cache."""
        try:
            cache_file = self._get_cache_file(key)
            meta_file = self._get_meta_file(key)
            
            if not cache_file.exists() or not meta_file.exists():
                return None
            
            # Check metadata for expiration
            with open(meta_file, 'r') as f:
                metadata = json.load(f)
            
            expires_at = metadata.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                self.delete(key)
                return None
            
            # Load data
            if self.serialization == "json":
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:  # pickle
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in file cache."""
        try:
            cache_file = self._get_cache_file(key)
            meta_file = self._get_meta_file(key)
            
            # Save data
            if self.serialization == "json":
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(value, f, indent=2, default=str)
            else:  # pickle
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
            
            # Save metadata
            expires_at = None
            if ttl is not None:
                expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
            
            metadata = {
                "key": key,
                "created_at": datetime.now().isoformat(),
                "expires_at": expires_at,
                "serialization": self.serialization,
            }
            
            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from file cache."""
        try:
            cache_file = self._get_cache_file(key)
            meta_file = self._get_meta_file(key)
            
            deleted = False
            if cache_file.exists():
                cache_file.unlink()
                deleted = True
            
            if meta_file.exists():
                meta_file.unlink()
                deleted = True
            
            return deleted
        
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            import shutil
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.meta_dir.mkdir(exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        removed_count = 0
        
        try:
            for meta_file in self.meta_dir.glob("*.json"):
                try:
                    with open(meta_file, 'r') as f:
                        metadata = json.load(f)
                    
                    expires_at = metadata.get("expires_at")
                    if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                        key = metadata["key"]
                        if self.delete(key):
                            removed_count += 1
                
                except Exception as e:
                    logger.warning(f"Failed to process metadata file {meta_file}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
        
        return removed_count
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        safe_key = self._make_safe_filename(key)
        extension = ".json" if self.serialization == "json" else ".pkl"
        return self.cache_dir / f"{safe_key}{extension}"
    
    def _get_meta_file(self, key: str) -> Path:
        """Get metadata file path for key."""
        safe_key = self._make_safe_filename(key)
        return self.meta_dir / f"{safe_key}.json"
    
    def _make_safe_filename(self, key: str) -> str:
        """Convert cache key to safe filename."""
        # Hash long keys to avoid filesystem limits
        if len(key) > 100:
            return hashlib.md5(key.encode()).hexdigest()
        
        # Replace unsafe characters
        safe_chars = "-_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(c if c in safe_chars else '_' for c in key)


class RedisCacheBackend(CacheBackend):
    """Redis cache backend for production use."""
    
    def __init__(self, redis_url: str):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not available. Install with: pip install redis")
        
        self.redis_client = redis.from_url(redis_url)
        
        # Test connection
        try:
            self.redis_client.ping()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            data = self.redis_client.get(key)
            if data is None:
                return None
            
            # Deserialize
            return json.loads(data.decode('utf-8'))
        
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            # Serialize
            data = json.dumps(value, default=str)
            
            # Set with TTL
            if ttl is not None:
                return self.redis_client.setex(key, ttl, data)
            else:
                return self.redis_client.set(key, data)
        
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            return self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Redis handles expiration automatically."""
        return 0  # Redis handles this automatically


class CacheManager:
    """Main cache manager that coordinates different cache backends."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.backend = self._create_backend()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
    
    def _create_backend(self) -> CacheBackend:
        """Create appropriate cache backend based on configuration."""
        if self.config.cache_type == "redis":
            if not self.config.redis_url:
                raise ValueError("Redis URL required for Redis cache")
            return RedisCacheBackend(self.config.redis_url)
        
        elif self.config.cache_type == "file":
            return FileCacheBackend(
                self.config.cache_dir,
                self.config.serialization,
                self.config.compression
            )
        
        elif self.config.cache_type == "memory":
            return MemoryCacheBackend(self.config.max_cache_size)
        
        else:
            raise ValueError(f"Unknown cache type: {self.config.cache_type}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = self.backend.get(key)
        
        if value is not None:
            self.stats["hits"] += 1
            logger.debug(f"Cache hit for key: {key}")
        else:
            self.stats["misses"] += 1
            logger.debug(f"Cache miss for key: {key}")
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if ttl is None:
            ttl = self.config.default_ttl
        
        success = self.backend.set(key, value, ttl)
        
        if success:
            self.stats["sets"] += 1
            logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
        else:
            logger.warning(f"Failed to set cache key: {key}")
        
        return success
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        success = self.backend.delete(key)
        
        if success:
            self.stats["deletes"] += 1
            logger.debug(f"Cache delete for key: {key}")
        
        return success
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self.backend.exists(key)
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        success = self.backend.clear()
        if success:
            self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
            logger.info("Cache cleared")
        return success
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        removed_count = self.backend.cleanup_expired()
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired cache entries")
        return removed_count
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }
    
    def make_key(self, *parts: str) -> str:
        """Create a cache key from multiple parts."""
        return ":".join(str(part) for part in parts)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_expired()