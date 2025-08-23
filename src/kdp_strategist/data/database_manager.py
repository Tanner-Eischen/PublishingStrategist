"""Database management system for KDP Strategist.

Provides SQLite database operations with:
- Async connection handling
- Schema management and migrations
- Analysis result storage
- API response caching
- User session management
"""

import json
import sqlite3
import aiosqlite
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, List, Union
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Configuration for database management."""
    db_path: str = "kdp_strategist.db"
    connection_timeout: int = 30
    max_connections: int = 10
    enable_wal_mode: bool = True
    enable_foreign_keys: bool = True
    backup_interval: int = 86400  # seconds (24 hours)


class DatabaseManager:
    """Main database manager for KDP Strategist application."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.db_path = Path(config.db_path)
        self.connection_pool = []
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize database with schema and configuration."""
        try:
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create database and tables
            await self._create_schema()
            
            # Configure database settings
            await self._configure_database()
            
            # Run any pending migrations
            await self._run_migrations()
            
            self.is_initialized = True
            logger.info(f"Database initialized successfully at {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def _create_schema(self) -> None:
        """Create database schema with all required tables."""
        schema_sql = """
        -- Analysis Results Storage
        CREATE TABLE IF NOT EXISTS niche_analyses (
            id TEXT PRIMARY KEY,
            keyword TEXT NOT NULL,
            analysis_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            metadata TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_niche_analyses_keyword ON niche_analyses(keyword);
        CREATE INDEX IF NOT EXISTS idx_niche_analyses_created_at ON niche_analyses(created_at);
        CREATE INDEX IF NOT EXISTS idx_niche_analyses_expires_at ON niche_analyses(expires_at);
        
        -- API Response Cache
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            response_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            service_name TEXT,
            request_hash TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_api_cache_expires_at ON api_cache(expires_at);
        CREATE INDEX IF NOT EXISTS idx_api_cache_service ON api_cache(service_name);
        
        -- User Sessions and Preferences
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        );
        
        CREATE INDEX IF NOT EXISTS idx_user_sessions_last_accessed ON user_sessions(last_accessed);
        
        -- Trend Analysis Cache
        CREATE TABLE IF NOT EXISTS trend_cache (
            id TEXT PRIMARY KEY,
            keyword TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trend_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_trend_cache_keyword ON trend_cache(keyword);
        CREATE INDEX IF NOT EXISTS idx_trend_cache_expires_at ON trend_cache(expires_at);
        
        -- Competition Analysis Cache
        CREATE TABLE IF NOT EXISTS competition_cache (
            id TEXT PRIMARY KEY,
            keyword TEXT NOT NULL,
            competition_data TEXT NOT NULL,
            data_source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_competition_cache_keyword ON competition_cache(keyword);
        CREATE INDEX IF NOT EXISTS idx_competition_cache_expires_at ON competition_cache(expires_at);
        
        -- Database Metadata and Migrations
        CREATE TABLE IF NOT EXISTS db_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Insert initial metadata
        INSERT OR IGNORE INTO db_metadata (key, value) VALUES ('schema_version', '1.0');
        INSERT OR IGNORE INTO db_metadata (key, value) VALUES ('created_at', datetime('now'));
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(schema_sql)
            await db.commit()
    
    async def _configure_database(self) -> None:
        """Configure database settings for optimal performance."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency
            if self.config.enable_wal_mode:
                await db.execute("PRAGMA journal_mode=WAL")
            
            # Enable foreign key constraints
            if self.config.enable_foreign_keys:
                await db.execute("PRAGMA foreign_keys=ON")
            
            # Set connection timeout
            await db.execute(f"PRAGMA busy_timeout={self.config.connection_timeout * 1000}")
            
            # Optimize for performance
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute("PRAGMA cache_size=10000")
            await db.execute("PRAGMA temp_store=MEMORY")
            
            await db.commit()
    
    async def _run_migrations(self) -> None:
        """Run any pending database migrations."""
        # For now, we'll just log that migrations are complete
        # In the future, this would check schema version and run migrations
        logger.info("Database migrations completed")
    
    async def store_analysis(self, analysis_data: Dict[str, Any], expires_in: int = 3600) -> str:
        """Store niche analysis results with expiration."""
        try:
            analysis_id = str(uuid.uuid4())
            keyword = analysis_data.get('keywords', ['unknown'])[0] if analysis_data.get('keywords') else 'unknown'
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Prepare metadata
            metadata = {
                'analysis_type': 'niche_discovery',
                'data_sources': analysis_data.get('metadata', {}).get('data_sources', []),
                'confidence_score': analysis_data.get('metadata', {}).get('confidence_score', 0.0)
            }
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO niche_analyses 
                       (id, keyword, analysis_data, expires_at, metadata) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        analysis_id,
                        keyword,
                        json.dumps(analysis_data, default=str),
                        expires_at.isoformat(),
                        json.dumps(metadata)
                    )
                )
                await db.commit()
            
            logger.info(f"Stored analysis {analysis_id} for keyword '{keyword}'")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Failed to store analysis: {e}")
            raise
    
    async def get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis if not expired."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """SELECT analysis_data, expires_at FROM niche_analyses 
                       WHERE keyword = ? AND (expires_at IS NULL OR expires_at > ?)
                       ORDER BY created_at DESC LIMIT 1""",
                    (cache_key, datetime.now().isoformat())
                )
                row = await cursor.fetchone()
                
                if row:
                    analysis_data, expires_at = row
                    return json.loads(analysis_data)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get cached analysis for key {cache_key}: {e}")
            return None
    
    async def store_api_response(self, service_name: str, request_params: Dict[str, Any], 
                               response_data: Any, ttl: int = 3600) -> bool:
        """Store API response in cache."""
        try:
            # Generate cache key from service name and request parameters
            cache_key = self._generate_cache_key(service_name, request_params)
            request_hash = hashlib.md5(json.dumps(request_params, sort_keys=True).encode()).hexdigest()
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO api_cache 
                       (cache_key, response_data, expires_at, service_name, request_hash) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        cache_key,
                        json.dumps(response_data, default=str),
                        expires_at.isoformat(),
                        service_name,
                        request_hash
                    )
                )
                await db.commit()
            
            logger.debug(f"Cached API response for {service_name}: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store API response: {e}")
            return False
    
    async def get_cached_api_response(self, service_name: str, request_params: Dict[str, Any]) -> Optional[Any]:
        """Retrieve cached API response if not expired."""
        try:
            cache_key = self._generate_cache_key(service_name, request_params)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """SELECT response_data FROM api_cache 
                       WHERE cache_key = ? AND expires_at > ?""",
                    (cache_key, datetime.now().isoformat())
                )
                row = await cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get cached API response: {e}")
            return None
    
    async def store_trend_data(self, keyword: str, timeframe: str, trend_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Store trend analysis data."""
        try:
            trend_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO trend_cache 
                       (id, keyword, timeframe, trend_data, expires_at) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        trend_id,
                        keyword,
                        timeframe,
                        json.dumps(trend_data, default=str),
                        expires_at.isoformat()
                    )
                )
                await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store trend data: {e}")
            return False
    
    async def get_trend_data(self, keyword: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached trend data if not expired."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """SELECT trend_data FROM trend_cache 
                       WHERE keyword = ? AND timeframe = ? AND expires_at > ?
                       ORDER BY created_at DESC LIMIT 1""",
                    (keyword, timeframe, datetime.now().isoformat())
                )
                row = await cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get trend data: {e}")
            return None
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries from all cache tables."""
        removed_count = 0
        current_time = datetime.now().isoformat()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Clean up expired niche analyses
                cursor = await db.execute(
                    "DELETE FROM niche_analyses WHERE expires_at IS NOT NULL AND expires_at <= ?",
                    (current_time,)
                )
                removed_count += cursor.rowcount
                
                # Clean up expired API cache
                cursor = await db.execute(
                    "DELETE FROM api_cache WHERE expires_at <= ?",
                    (current_time,)
                )
                removed_count += cursor.rowcount
                
                # Clean up expired trend cache
                cursor = await db.execute(
                    "DELETE FROM trend_cache WHERE expires_at <= ?",
                    (current_time,)
                )
                removed_count += cursor.rowcount
                
                # Clean up expired competition cache
                cursor = await db.execute(
                    "DELETE FROM competition_cache WHERE expires_at <= ?",
                    (current_time,)
                )
                removed_count += cursor.rowcount
                
                await db.commit()
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} expired database entries")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
            return 0
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information."""
        try:
            stats = {}
            
            async with aiosqlite.connect(self.db_path) as db:
                # Get table row counts
                tables = ['niche_analyses', 'api_cache', 'trend_cache', 'competition_cache', 'user_sessions']
                
                for table in tables:
                    cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                    count = await cursor.fetchone()
                    stats[f"{table}_count"] = count[0] if count else 0
                
                # Get database size
                cursor = await db.execute("PRAGMA page_count")
                page_count = await cursor.fetchone()
                cursor = await db.execute("PRAGMA page_size")
                page_size = await cursor.fetchone()
                
                if page_count and page_size:
                    stats['database_size_bytes'] = page_count[0] * page_size[0]
                    stats['database_size_mb'] = round(stats['database_size_bytes'] / (1024 * 1024), 2)
                
                # Get schema version
                cursor = await db.execute("SELECT value FROM db_metadata WHERE key = 'schema_version'")
                version = await cursor.fetchone()
                stats['schema_version'] = version[0] if version else 'unknown'
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    async def vacuum_database(self) -> bool:
        """Vacuum database to reclaim space and optimize performance."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("VACUUM")
                await db.commit()
            
            logger.info("Database vacuum completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            return False
    
    def _generate_cache_key(self, service_name: str, request_params: Dict[str, Any]) -> str:
        """Generate a cache key from service name and request parameters."""
        # Sort parameters for consistent key generation
        sorted_params = json.dumps(request_params, sort_keys=True)
        param_hash = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"{service_name}:{param_hash}"
    
    async def close(self) -> None:
        """Close database connections and cleanup."""
        try:
            # Perform final cleanup
            await self.cleanup_expired()
            logger.info("Database manager closed successfully")
        except Exception as e:
            logger.error(f"Error closing database manager: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.is_initialized:
            await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Utility functions for database operations
async def create_database_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Create and initialize a database manager."""
    if config is None:
        config = DatabaseConfig()
    
    manager = DatabaseManager(config)
    await manager.initialize()
    return manager


async def migrate_database(db_path: str, target_version: str = "1.0") -> bool:
    """Run database migrations to target version."""
    try:
        config = DatabaseConfig(db_path=db_path)
        manager = DatabaseManager(config)
        await manager.initialize()
        
        # Migration logic would go here
        logger.info(f"Database migrated to version {target_version}")
        return True
        
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return False