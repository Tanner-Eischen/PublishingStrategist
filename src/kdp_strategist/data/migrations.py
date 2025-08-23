"""Database migration system for KDP Strategist.

Provides version-controlled database schema migrations with:
- Schema version tracking
- Forward and backward migration support
- Data integrity validation
- Rollback capabilities
"""

import json
import logging
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a single database migration."""
    version: str
    description: str
    up_sql: str
    down_sql: str = ""
    validation_func: Optional[Callable] = None


class MigrationManager:
    """Manages database schema migrations."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.migrations: List[Migration] = []
        self._register_migrations()
    
    def _register_migrations(self) -> None:
        """Register all available migrations in order."""
        
        # Migration 1.0 - Initial schema
        self.migrations.append(Migration(
            version="1.0",
            description="Initial database schema with core tables",
            up_sql="""
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
            
            -- Migration tracking
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rollback_sql TEXT
            );
            
            -- Insert initial metadata
            INSERT OR IGNORE INTO db_metadata (key, value) VALUES ('schema_version', '1.0');
            INSERT OR IGNORE INTO db_metadata (key, value) VALUES ('created_at', datetime('now'));
            """,
            down_sql="""
            DROP TABLE IF EXISTS niche_analyses;
            DROP TABLE IF EXISTS api_cache;
            DROP TABLE IF EXISTS user_sessions;
            DROP TABLE IF EXISTS trend_cache;
            DROP TABLE IF EXISTS competition_cache;
            DROP TABLE IF EXISTS db_metadata;
            DROP TABLE IF EXISTS schema_migrations;
            """
        ))
        
        # Migration 1.1 - Enhanced indexing and performance optimizations
        self.migrations.append(Migration(
            version="1.1",
            description="Enhanced indexing and performance optimizations",
            up_sql="""
            -- Add composite indexes for better query performance
            CREATE INDEX IF NOT EXISTS idx_niche_analyses_keyword_created ON niche_analyses(keyword, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_api_cache_service_expires ON api_cache(service_name, expires_at);
            CREATE INDEX IF NOT EXISTS idx_trend_cache_keyword_timeframe ON trend_cache(keyword, timeframe);
            
            -- Add full-text search support for analysis data
            CREATE VIRTUAL TABLE IF NOT EXISTS niche_analyses_fts USING fts5(
                id, keyword, analysis_data, content='niche_analyses', content_rowid='rowid'
            );
            
            -- Populate FTS table
            INSERT OR IGNORE INTO niche_analyses_fts(id, keyword, analysis_data)
            SELECT id, keyword, analysis_data FROM niche_analyses;
            
            -- Add triggers to keep FTS table in sync
            CREATE TRIGGER IF NOT EXISTS niche_analyses_fts_insert AFTER INSERT ON niche_analyses BEGIN
                INSERT INTO niche_analyses_fts(id, keyword, analysis_data) 
                VALUES (new.id, new.keyword, new.analysis_data);
            END;
            
            CREATE TRIGGER IF NOT EXISTS niche_analyses_fts_delete AFTER DELETE ON niche_analyses BEGIN
                DELETE FROM niche_analyses_fts WHERE id = old.id;
            END;
            
            CREATE TRIGGER IF NOT EXISTS niche_analyses_fts_update AFTER UPDATE ON niche_analyses BEGIN
                DELETE FROM niche_analyses_fts WHERE id = old.id;
                INSERT INTO niche_analyses_fts(id, keyword, analysis_data) 
                VALUES (new.id, new.keyword, new.analysis_data);
            END;
            """,
            down_sql="""
            DROP TRIGGER IF EXISTS niche_analyses_fts_update;
            DROP TRIGGER IF EXISTS niche_analyses_fts_delete;
            DROP TRIGGER IF EXISTS niche_analyses_fts_insert;
            DROP TABLE IF EXISTS niche_analyses_fts;
            DROP INDEX IF EXISTS idx_trend_cache_keyword_timeframe;
            DROP INDEX IF EXISTS idx_api_cache_service_expires;
            DROP INDEX IF EXISTS idx_niche_analyses_keyword_created;
            """
        ))
    
    async def get_current_version(self) -> Optional[str]:
        """Get the current database schema version."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # First check if metadata table exists
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'"
                )
                if not await cursor.fetchone():
                    return None
                
                # Get current version
                cursor = await db.execute(
                    "SELECT value FROM db_metadata WHERE key = 'schema_version'"
                )
                row = await cursor.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"Failed to get current database version: {e}")
            return None
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check if migrations table exists
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
                )
                if not await cursor.fetchone():
                    return []
                
                cursor = await db.execute(
                    "SELECT version FROM schema_migrations ORDER BY applied_at"
                )
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    async def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Execute migration SQL
                await db.executescript(migration.up_sql)
                
                # Record migration in tracking table
                await db.execute(
                    """INSERT OR REPLACE INTO schema_migrations 
                       (version, description, rollback_sql) VALUES (?, ?, ?)""",
                    (migration.version, migration.description, migration.down_sql)
                )
                
                # Update schema version in metadata
                await db.execute(
                    """INSERT OR REPLACE INTO db_metadata (key, value, updated_at) 
                       VALUES ('schema_version', ?, datetime('now'))""",
                    (migration.version,)
                )
                
                await db.commit()
                
                # Run validation if provided
                if migration.validation_func:
                    if not await migration.validation_func(db):
                        raise Exception(f"Migration {migration.version} validation failed")
                
                logger.info(f"Applied migration {migration.version}: {migration.description}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            return False
    
    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get rollback SQL
                cursor = await db.execute(
                    "SELECT rollback_sql FROM schema_migrations WHERE version = ?",
                    (version,)
                )
                row = await cursor.fetchone()
                
                if not row or not row[0]:
                    logger.error(f"No rollback SQL found for migration {version}")
                    return False
                
                # Execute rollback SQL
                await db.executescript(row[0])
                
                # Remove migration record
                await db.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (version,)
                )
                
                # Update schema version to previous version
                cursor = await db.execute(
                    """SELECT version FROM schema_migrations 
                       ORDER BY applied_at DESC LIMIT 1"""
                )
                prev_row = await cursor.fetchone()
                prev_version = prev_row[0] if prev_row else "0.0"
                
                await db.execute(
                    """UPDATE db_metadata SET value = ?, updated_at = datetime('now') 
                       WHERE key = 'schema_version'""",
                    (prev_version,)
                )
                
                await db.commit()
                
                logger.info(f"Rolled back migration {version}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False
    
    async def migrate_to_latest(self) -> bool:
        """Migrate database to the latest schema version."""
        try:
            current_version = await self.get_current_version()
            applied_migrations = await self.get_applied_migrations()
            
            logger.info(f"Current database version: {current_version}")
            logger.info(f"Applied migrations: {applied_migrations}")
            
            # Apply missing migrations
            success_count = 0
            for migration in self.migrations:
                if migration.version not in applied_migrations:
                    logger.info(f"Applying migration {migration.version}...")
                    if await self.apply_migration(migration):
                        success_count += 1
                    else:
                        logger.error(f"Failed to apply migration {migration.version}")
                        return False
            
            if success_count > 0:
                logger.info(f"Successfully applied {success_count} migrations")
            else:
                logger.info("Database is already up to date")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate to latest version: {e}")
            return False
    
    async def validate_schema(self) -> Dict[str, Any]:
        """Validate database schema integrity."""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "table_counts": {},
            "index_status": {}
        }
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check required tables exist
                required_tables = [
                    'niche_analyses', 'api_cache', 'user_sessions',
                    'trend_cache', 'competition_cache', 'db_metadata', 'schema_migrations'
                ]
                
                for table in required_tables:
                    cursor = await db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)
                    )
                    if not await cursor.fetchone():
                        validation_results["errors"].append(f"Missing required table: {table}")
                        validation_results["valid"] = False
                    else:
                        # Get row count
                        cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                        count = await cursor.fetchone()
                        validation_results["table_counts"][table] = count[0] if count else 0
                
                # Check required indexes exist
                required_indexes = [
                    'idx_niche_analyses_keyword',
                    'idx_api_cache_expires_at',
                    'idx_user_sessions_last_accessed',
                    'idx_trend_cache_keyword',
                    'idx_competition_cache_keyword'
                ]
                
                for index in required_indexes:
                    cursor = await db.execute(
                        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                        (index,)
                    )
                    validation_results["index_status"][index] = bool(await cursor.fetchone())
                    if not validation_results["index_status"][index]:
                        validation_results["warnings"].append(f"Missing index: {index}")
                
                # Check for orphaned data
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM api_cache WHERE expires_at <= datetime('now')"
                )
                expired_count = await cursor.fetchone()
                if expired_count and expired_count[0] > 0:
                    validation_results["warnings"].append(
                        f"{expired_count[0]} expired entries in api_cache"
                    )
                
        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Schema validation error: {e}")
        
        return validation_results


async def initialize_database(db_path: str) -> bool:
    """Initialize a new database with the latest schema."""
    try:
        migration_manager = MigrationManager(db_path)
        success = await migration_manager.migrate_to_latest()
        
        if success:
            logger.info(f"Database initialized successfully at {db_path}")
        else:
            logger.error(f"Failed to initialize database at {db_path}")
        
        return success
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def upgrade_database(db_path: str, target_version: Optional[str] = None) -> bool:
    """Upgrade database to target version or latest."""
    try:
        migration_manager = MigrationManager(db_path)
        
        if target_version:
            # Apply specific migrations up to target version
            applied_migrations = await migration_manager.get_applied_migrations()
            
            for migration in migration_manager.migrations:
                if migration.version == target_version:
                    break
                if migration.version not in applied_migrations:
                    if not await migration_manager.apply_migration(migration):
                        return False
            
            logger.info(f"Database upgraded to version {target_version}")
        else:
            # Upgrade to latest
            success = await migration_manager.migrate_to_latest()
            if not success:
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Database upgrade failed: {e}")
        return False


async def validate_database(db_path: str) -> Dict[str, Any]:
    """Validate database schema and return detailed results."""
    try:
        migration_manager = MigrationManager(db_path)
        return await migration_manager.validate_schema()
        
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return {
            "valid": False,
            "errors": [f"Validation error: {e}"],
            "warnings": [],
            "table_counts": {},
            "index_status": {}
        }