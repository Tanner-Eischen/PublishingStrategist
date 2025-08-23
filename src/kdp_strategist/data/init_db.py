#!/usr/bin/env python3
"""Database initialization script for KDP Strategist.

This script can be run standalone to initialize or upgrade the database.
It provides command-line interface for database management operations.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import directly from the modules to avoid circular imports
from src.kdp_strategist.data.database_manager import DatabaseManager, DatabaseConfig
from src.kdp_strategist.data.migrations import (
    initialize_database,
    upgrade_database,
    validate_database,
    MigrationManager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_command(db_path: str, force: bool = False) -> bool:
    """Initialize a new database."""
    db_file = Path(db_path)
    
    if db_file.exists() and not force:
        logger.error(f"Database already exists at {db_path}. Use --force to overwrite.")
        return False
    
    if force and db_file.exists():
        logger.info(f"Removing existing database at {db_path}")
        db_file.unlink()
    
    logger.info(f"Initializing database at {db_path}")
    success = await initialize_database(db_path)
    
    if success:
        logger.info("Database initialization completed successfully")
        
        # Validate the new database
        validation = await validate_database(db_path)
        if validation["valid"]:
            logger.info("Database validation passed")
        else:
            logger.warning("Database validation found issues:")
            for error in validation["errors"]:
                logger.error(f"  - {error}")
    else:
        logger.error("Database initialization failed")
    
    return success


async def upgrade_command(db_path: str, target_version: Optional[str] = None) -> bool:
    """Upgrade existing database."""
    db_file = Path(db_path)
    
    if not db_file.exists():
        logger.error(f"Database does not exist at {db_path}. Use 'init' command first.")
        return False
    
    logger.info(f"Upgrading database at {db_path}")
    if target_version:
        logger.info(f"Target version: {target_version}")
    else:
        logger.info("Upgrading to latest version")
    
    success = await upgrade_database(db_path, target_version)
    
    if success:
        logger.info("Database upgrade completed successfully")
    else:
        logger.error("Database upgrade failed")
    
    return success


async def validate_command(db_path: str) -> bool:
    """Validate database schema and integrity."""
    db_file = Path(db_path)
    
    if not db_file.exists():
        logger.error(f"Database does not exist at {db_path}")
        return False
    
    logger.info(f"Validating database at {db_path}")
    validation = await validate_database(db_path)
    
    if validation["valid"]:
        logger.info("✅ Database validation passed")
    else:
        logger.error("❌ Database validation failed")
        
        if validation["errors"]:
            logger.error("Errors found:")
            for error in validation["errors"]:
                logger.error(f"  - {error}")
        
        if validation["warnings"]:
            logger.warning("Warnings:")
            for warning in validation["warnings"]:
                logger.warning(f"  - {warning}")
    
    # Display table statistics
    if validation["table_counts"]:
        logger.info("Table statistics:")
        for table, count in validation["table_counts"].items():
            logger.info(f"  {table}: {count} rows")
    
    # Display index status
    if validation["index_status"]:
        logger.info("Index status:")
        for index, exists in validation["index_status"].items():
            status = "✅" if exists else "❌"
            logger.info(f"  {status} {index}")
    
    return validation["valid"]


async def status_command(db_path: str) -> bool:
    """Show database status and migration information."""
    db_file = Path(db_path)
    
    if not db_file.exists():
        logger.error(f"Database does not exist at {db_path}")
        return False
    
    try:
        migration_manager = MigrationManager(db_path)
        current_version = await migration_manager.get_current_version()
        applied_migrations = await migration_manager.get_applied_migrations()
        
        logger.info(f"Database: {db_path}")
        logger.info(f"Current version: {current_version or 'Unknown'}")
        logger.info(f"Applied migrations: {len(applied_migrations)}")
        
        if applied_migrations:
            logger.info("Migration history:")
            for version in applied_migrations:
                logger.info(f"  ✅ {version}")
        
        # Show available migrations
        available_versions = [m.version for m in migration_manager.migrations]
        pending_migrations = [v for v in available_versions if v not in applied_migrations]
        
        if pending_migrations:
            logger.info("Pending migrations:")
            for version in pending_migrations:
                logger.info(f"  ⏳ {version}")
        else:
            logger.info("✅ Database is up to date")
        
        # Show database stats
        config = DatabaseConfig(db_path=db_path)
        db_manager = DatabaseManager(config)
        await db_manager.initialize()
        stats = await db_manager.get_database_stats()
        
        if stats:
            logger.info("Database statistics:")
            for key, value in stats.items():
                if key.endswith('_count'):
                    table_name = key.replace('_count', '')
                    logger.info(f"  {table_name}: {value} records")
                elif key == 'database_size_mb':
                    logger.info(f"  Size: {value} MB")
        
        await db_manager.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        return False


async def cleanup_command(db_path: str, dry_run: bool = False) -> bool:
    """Clean up expired entries from database."""
    db_file = Path(db_path)
    
    if not db_file.exists():
        logger.error(f"Database does not exist at {db_path}")
        return False
    
    try:
        config = DatabaseConfig(db_path=db_path)
        db_manager = DatabaseManager(config)
        await db_manager.initialize()
        
        if dry_run:
            logger.info("Dry run mode - no changes will be made")
            # In a real implementation, we'd count expired entries without deleting
            logger.info("Would clean up expired entries")
        else:
            logger.info("Cleaning up expired entries...")
            removed_count = await db_manager.cleanup_expired()
            logger.info(f"Removed {removed_count} expired entries")
            
            # Vacuum database to reclaim space
            logger.info("Vacuuming database...")
            if await db_manager.vacuum_database():
                logger.info("Database vacuum completed")
            else:
                logger.warning("Database vacuum failed")
        
        await db_manager.close()
        return True
        
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")
        return False


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="KDP Strategist Database Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init                          # Initialize database with default name
  %(prog)s init --db custom.db           # Initialize database with custom name
  %(prog)s init --force                  # Force overwrite existing database
  %(prog)s upgrade                       # Upgrade to latest version
  %(prog)s upgrade --version 1.1         # Upgrade to specific version
  %(prog)s validate                      # Validate database schema
  %(prog)s status                        # Show database status
  %(prog)s cleanup                       # Clean up expired entries
  %(prog)s cleanup --dry-run             # Show what would be cleaned up
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add common arguments to all subparsers
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        '--db', '--database',
        default='kdp_strategist.db',
        help='Database file path (default: kdp_strategist.db)'
    )
    parent_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Init command
    init_parser = subparsers.add_parser('init', parents=[parent_parser], help='Initialize new database')
    init_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force overwrite existing database'
    )
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser('upgrade', parents=[parent_parser], help='Upgrade database schema')
    upgrade_parser.add_argument(
        '--version', '-t',
        help='Target version (default: latest)'
    )
    
    # Validate command
    subparsers.add_parser('validate', parents=[parent_parser], help='Validate database schema')
    
    # Status command
    subparsers.add_parser('status', parents=[parent_parser], help='Show database status')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', parents=[parent_parser], help='Clean up expired entries')
    cleanup_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be cleaned up without making changes'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Run the appropriate command
    try:
        if args.command == 'init':
            success = asyncio.run(init_command(args.db, args.force))
        elif args.command == 'upgrade':
            success = asyncio.run(upgrade_command(args.db, args.version))
        elif args.command == 'validate':
            success = asyncio.run(validate_command(args.db))
        elif args.command == 'status':
            success = asyncio.run(status_command(args.db))
        elif args.command == 'cleanup':
            success = asyncio.run(cleanup_command(args.db, args.dry_run))
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())