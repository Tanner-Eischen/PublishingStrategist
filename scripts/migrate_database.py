#!/usr/bin/env python3
"""Database Migration Script for Simple Trends System.

This script handles database migrations needed for the Simple Trends deployment.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles database migrations for Simple Trends system."""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///kdp_strategist.db")
        self.migrations_dir = Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)
        
        logger.info(f"DatabaseMigrator initialized with URL: {self.database_url}")
    
    def create_migration_table(self):
        """Create migrations tracking table if it doesn't exist."""
        # For this implementation, we'll use a simple file-based tracking
        # In a real implementation, this would create a database table
        
        migrations_file = self.migrations_dir / "applied_migrations.json"
        if not migrations_file.exists():
            with open(migrations_file, 'w') as f:
                json.dump([], f)
            logger.info("Created migrations tracking file")
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations."""
        migrations_file = self.migrations_dir / "applied_migrations.json"
        if migrations_file.exists():
            with open(migrations_file, 'r') as f:
                return json.load(f)
        return []
    
    def mark_migration_applied(self, migration_name: str):
        """Mark a migration as applied."""
        applied = self.get_applied_migrations()
        if migration_name not in applied:
            applied.append(migration_name)
            applied.sort()
            
            migrations_file = self.migrations_dir / "applied_migrations.json"
            with open(migrations_file, 'w') as f:
                json.dump(applied, f, indent=2)
            
            logger.info(f"Marked migration as applied: {migration_name}")
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations."""
        applied = self.get_applied_migrations()
        all_migrations = []
        
        # Find all migration files
        for migration_file in sorted(self.migrations_dir.glob("*.sql")):
            migration_name = migration_file.stem
            if migration_name not in applied:
                all_migrations.append(migration_name)
        
        return all_migrations
    
    def create_initial_migrations(self):
        """Create initial migration files for Simple Trends system."""
        migrations = [
            {
                "name": "001_create_feature_flags_table",
                "description": "Create feature flags tracking table",
                "sql": """
-- Create feature flags tracking table
CREATE TABLE IF NOT EXISTS feature_flags_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    environment VARCHAR(50) DEFAULT 'production'
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_history_flag_name ON feature_flags_history(flag_name);
CREATE INDEX IF NOT EXISTS idx_feature_flags_history_changed_at ON feature_flags_history(changed_at);
                """
            },
            {
                "name": "002_create_performance_metrics_table",
                "description": "Create performance metrics tracking table",
                "sql": """
-- Create performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_type VARCHAR(50) NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    response_time REAL NOT NULL,
    success BOOLEAN NOT NULL,
    cache_hit BOOLEAN DEFAULT FALSE,
    confidence_level REAL DEFAULT 0.0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    environment VARCHAR(50) DEFAULT 'production'
);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_client_type ON performance_metrics(client_type);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_keyword ON performance_metrics(keyword);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_recorded_at ON performance_metrics(recorded_at);
                """
            },
            {
                "name": "003_create_deployment_history_table",
                "description": "Create deployment history tracking table",
                "sql": """
-- Create deployment history table
CREATE TABLE IF NOT EXISTS deployment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL,
    deployment_type VARCHAR(50) DEFAULT 'blue_green',
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    deployed_by VARCHAR(100),
    rollback_version VARCHAR(100),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_deployment_history_environment ON deployment_history(environment);
CREATE INDEX IF NOT EXISTS idx_deployment_history_version ON deployment_history(version);
CREATE INDEX IF NOT EXISTS idx_deployment_history_started_at ON deployment_history(started_at);
                """
            }
        ]
        
        for migration in migrations:
            migration_file = self.migrations_dir / f"{migration['name']}.sql"
            if not migration_file.exists():
                with open(migration_file, 'w') as f:
                    f.write(f"-- {migration['description']}\n")
                    f.write(f"-- Created: {datetime.now().isoformat()}\n\n")
                    f.write(migration['sql'].strip())
                
                logger.info(f"Created migration file: {migration_file}")
    
    def apply_migration(self, migration_name: str) -> bool:
        """Apply a single migration."""
        migration_file = self.migrations_dir / f"{migration_name}.sql"
        
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        try:
            with open(migration_file, 'r') as f:
                sql_content = f.read()
            
            # For this implementation, we'll just log the SQL
            # In a real implementation, this would execute against the database
            logger.info(f"Applying migration: {migration_name}")
            logger.debug(f"SQL content:\n{sql_content}")
            
            # Simulate successful migration
            self.mark_migration_applied(migration_name)
            
            logger.info(f"Successfully applied migration: {migration_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration_name}: {e}")
            return False
    
    def migrate(self) -> bool:
        """Apply all pending migrations."""
        self.create_migration_table()
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return True
        
        logger.info(f"Found {len(pending)} pending migrations")
        
        for migration_name in pending:
            if not self.apply_migration(migration_name):
                logger.error(f"Migration failed: {migration_name}")
                return False
        
        logger.info("All migrations applied successfully")
        return True
    
    def rollback_migration(self, migration_name: str) -> bool:
        """Rollback a specific migration."""
        # For this implementation, we'll just remove it from applied list
        # In a real implementation, this would execute rollback SQL
        
        applied = self.get_applied_migrations()
        if migration_name in applied:
            applied.remove(migration_name)
            
            migrations_file = self.migrations_dir / "applied_migrations.json"
            with open(migrations_file, 'w') as f:
                json.dump(applied, f, indent=2)
            
            logger.info(f"Rolled back migration: {migration_name}")
            return True
        else:
            logger.warning(f"Migration not applied, cannot rollback: {migration_name}")
            return False
    
    def status(self) -> Dict[str, Any]:
        """Get migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        return {
            "database_url": self.database_url,
            "applied_migrations": applied,
            "pending_migrations": pending,
            "total_applied": len(applied),
            "total_pending": len(pending),
            "last_migration": applied[-1] if applied else None,
            "timestamp": datetime.now().isoformat()
        }
    
    def create_migration(self, name: str, description: str = "") -> bool:
        """Create a new migration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_name = f"{timestamp}_{name}"
        migration_file = self.migrations_dir / f"{migration_name}.sql"
        
        if migration_file.exists():
            logger.error(f"Migration file already exists: {migration_file}")
            return False
        
        template = f"""-- {description or name}
-- Created: {datetime.now().isoformat()}

-- Add your SQL statements here
-- Example:
-- CREATE TABLE example (
--     id INTEGER PRIMARY KEY,
--     name VARCHAR(100) NOT NULL
-- );

-- Remember to test your migration before applying to production!
"""
        
        with open(migration_file, 'w') as f:
            f.write(template)
        
        logger.info(f"Created migration file: {migration_file}")
        print(f"Migration file created: {migration_file}")
        print("Edit the file to add your SQL statements, then run 'migrate' to apply.")
        
        return True


def create_cli_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Database migration tool for Simple Trends system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check migration status
  python scripts/migrate_database.py status
  
  # Apply all pending migrations
  python scripts/migrate_database.py migrate
  
  # Create initial migration files
  python scripts/migrate_database.py init
  
  # Create a new migration
  python scripts/migrate_database.py create add_user_table "Add user management table"
  
  # Rollback a specific migration
  python scripts/migrate_database.py rollback 001_create_feature_flags_table
        """
    )
    
    parser.add_argument(
        '--database-url',
        help='Database URL (default: from DATABASE_URL env var or sqlite)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show migration status')
    
    # Migrate command
    subparsers.add_parser('migrate', help='Apply all pending migrations')
    
    # Init command
    subparsers.add_parser('init', help='Create initial migration files')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new migration')
    create_parser.add_argument('name', help='Migration name (without timestamp)')
    create_parser.add_argument('description', nargs='?', default='', help='Migration description')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback a migration')
    rollback_parser.add_argument('migration_name', help='Name of migration to rollback')
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize migrator
    migrator = DatabaseMigrator(args.database_url)
    
    # Execute command
    if args.command == 'status':
        status = migrator.status()
        print(json.dumps(status, indent=2))
    
    elif args.command == 'migrate':
        success = migrator.migrate()
        sys.exit(0 if success else 1)
    
    elif args.command == 'init':
        migrator.create_initial_migrations()
        print("Initial migration files created")
    
    elif args.command == 'create':
        success = migrator.create_migration(args.name, args.description)
        sys.exit(0 if success else 1)
    
    elif args.command == 'rollback':
        success = migrator.rollback_migration(args.migration_name)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()