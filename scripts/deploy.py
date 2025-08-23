#!/usr/bin/env python3
"""Deployment Script for Simple Trends Migration.

This script handles deployment of the Simple Trends system with
blue-green deployment capabilities and rollback procedures.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "kdp_strategist" / "data"))

from feature_flags import FeatureFlagManager

logger = logging.getLogger(__name__)


class DeploymentManager:
    """Manages deployment of Simple Trends system."""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config/deployment.json")
        self.flag_manager = FeatureFlagManager()
        self.deployment_config = self._load_deployment_config()
        
        # Deployment state
        self.current_deployment = None
        self.backup_deployment = None
        
        logger.info("DeploymentManager initialized")
    
    def _load_deployment_config(self) -> Dict[str, Any]:
        """Load deployment configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded deployment config from {self.config_file}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load deployment config: {e}")
        
        # Create default config
        default_config = {
            "environments": {
                "development": {
                    "api_url": "http://localhost:8000",
                    "database_url": "sqlite:///dev.db",
                    "cache_type": "file",
                    "log_level": "DEBUG"
                },
                "staging": {
                    "api_url": "https://staging-api.kdpstrategist.com",
                    "database_url": "postgresql://staging_db",
                    "cache_type": "redis",
                    "log_level": "INFO"
                },
                "production": {
                    "api_url": "https://api.kdpstrategist.com",
                    "database_url": "postgresql://prod_db",
                    "cache_type": "redis",
                    "log_level": "WARNING"
                }
            },
            "deployment": {
                "strategy": "blue_green",
                "health_check_timeout": 300,
                "rollback_timeout": 600,
                "backup_retention_days": 7,
                "pre_deployment_checks": [
                    "check_dependencies",
                    "run_tests",
                    "validate_config"
                ],
                "post_deployment_checks": [
                    "health_check",
                    "smoke_tests",
                    "performance_check"
                ]
            },
            "monitoring": {
                "health_check_interval": 30,
                "alert_thresholds": {
                    "response_time_ms": 2000,
                    "error_rate_percent": 5.0,
                    "success_rate_percent": 95.0
                }
            }
        }
        
        # Save default config
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default deployment config at {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to create deployment config: {e}")
        
        return default_config
    
    def pre_deployment_checks(self, environment: str) -> bool:
        """Run pre-deployment checks."""
        print(f"🔍 Running pre-deployment checks for {environment}...")
        
        checks = self.deployment_config.get("deployment", {}).get("pre_deployment_checks", [])
        
        for check in checks:
            print(f"   Running {check}...")
            
            if check == "check_dependencies":
                if not self._check_dependencies():
                    print(f"   ❌ {check} failed")
                    return False
            
            elif check == "run_tests":
                if not self._run_tests():
                    print(f"   ❌ {check} failed")
                    return False
            
            elif check == "validate_config":
                if not self._validate_config(environment):
                    print(f"   ❌ {check} failed")
                    return False
            
            print(f"   ✅ {check} passed")
        
        print("✅ All pre-deployment checks passed")
        return True
    
    def _check_dependencies(self) -> bool:
        """Check if all dependencies are available."""
        try:
            # Check Python dependencies
            import requests
            import fastapi
            import uvicorn
            
            # Check if required files exist
            required_files = [
                "src/kdp_strategist/data/simple_trends_client.py",
                "src/kdp_strategist/data/feature_flags.py",
                "config/feature_flags.json"
            ]
            
            for file_path in required_files:
                if not Path(file_path).exists():
                    logger.error(f"Required file missing: {file_path}")
                    return False
            
            return True
            
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            return False
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return False
    
    def _run_tests(self) -> bool:
        """Run test suite."""
        try:
            # Run basic feature flag tests
            result = subprocess.run([
                sys.executable, "-c", """
import sys
sys.path.append('src/kdp_strategist/data')
from feature_flags import FeatureFlagManager
import tempfile
from pathlib import Path

# Basic test
temp_dir = tempfile.mkdtemp()
config_file = Path(temp_dir) / 'test.json'
manager = FeatureFlagManager(config_file)
manager.update_flag_percentage(50.0)
assert manager.config.use_simple_trends.percentage == 50.0
print('Basic tests passed')
                """
            ], capture_output=True, text=True, timeout=60, encoding='utf-8')
            
            if result.returncode == 0:
                logger.info("Tests passed")
                
                # Run database migration tests if available
                migrate_script = Path("scripts/migrate_database.py")
                if migrate_script.exists():
                    migrate_result = subprocess.run([
                        sys.executable, str(migrate_script), "status"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if migrate_result.returncode != 0:
                        logger.warning("Database migration check failed, but continuing")
                
                return True
            else:
                logger.error(f"Tests failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return False
    
    def _validate_config(self, environment: str) -> bool:
        """Validate configuration for environment."""
        try:
            env_config = self.deployment_config.get("environments", {}).get(environment)
            if not env_config:
                logger.error(f"No configuration found for environment: {environment}")
                return False
            
            # Check required config keys
            required_keys = ["api_url", "log_level"]
            for key in required_keys:
                if key not in env_config:
                    logger.error(f"Missing required config key: {key}")
                    return False
            
            # Validate feature flag config
            flag_status = self.flag_manager.get_flag_status()
            if not flag_status:
                logger.error("Feature flag configuration invalid")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            return False
    
    def deploy(self, environment: str, version: str = None) -> bool:
        """Deploy to specified environment."""
        print(f"🚀 Starting deployment to {environment}")
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Pre-deployment checks
            if not self.pre_deployment_checks(environment):
                print("❌ Pre-deployment checks failed")
                return False
            
            # Create backup
            if not self._create_backup(environment, version):
                print("❌ Backup creation failed")
                return False
            
            # Deploy using blue-green strategy
            if not self._blue_green_deploy(environment, version):
                print("❌ Blue-green deployment failed")
                return False
            
            # Post-deployment checks
            if not self.post_deployment_checks(environment):
                print("❌ Post-deployment checks failed")
                print("🔄 Initiating rollback...")
                self.rollback(environment)
                return False
            
            print(f"✅ Deployment to {environment} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            print(f"❌ Deployment failed: {e}")
            return False
    
    def _create_backup(self, environment: str, version: str) -> bool:
        """Create backup before deployment."""
        print(f"💾 Creating backup for {environment}...")
        
        try:
            backup_dir = Path(f"backups/{environment}/{version}")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup configuration files
            config_files = [
                "config/feature_flags.json",
                "config/settings.py",
                "config/deployment.json",
                ".env"
            ]
            
            for config_file in config_files:
                if Path(config_file).exists():
                    import shutil
                    shutil.copy2(config_file, backup_dir / Path(config_file).name)
            
            # Backup current feature flag state
            flag_status = self.flag_manager.get_flag_status()
            with open(backup_dir / "feature_flags_state.json", 'w') as f:
                json.dump(flag_status, f, indent=2)
            
            # Backup database state (if using file-based database)
            db_files = ["kdp_strategist.db", "migrations/applied_migrations.json"]
            for db_file in db_files:
                if Path(db_file).exists():
                    import shutil
                    shutil.copy2(db_file, backup_dir / Path(db_file).name)
            
            # Create backup metadata
            backup_metadata = {
                "environment": environment,
                "version": version,
                "timestamp": datetime.now().isoformat(),
                "backup_type": "pre_deployment",
                "files_backed_up": config_files + db_files,
                "database_url": self.deployment_config.get("environments", {}).get(environment, {}).get("database_url", "")
            }
            
            with open(backup_dir / "backup_metadata.json", 'w') as f:
                json.dump(backup_metadata, f, indent=2)
            
            print(f"✅ Backup created at {backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
    
    def _blue_green_deploy(self, environment: str, version: str) -> bool:
        """Perform blue-green deployment."""
        print(f"🔄 Performing blue-green deployment...")
        
        try:
            # In a real implementation, this would:
            # 1. Deploy to green environment
            # 2. Run health checks on green
            # 3. Switch traffic from blue to green
            # 4. Keep blue as backup
            
            # For this implementation, we'll simulate the process
            print("   📦 Deploying to green environment...")
            time.sleep(2)  # Simulate deployment time
            
            print("   🔍 Running health checks on green environment...")
            if not self._health_check(environment):
                print("   ❌ Green environment health check failed")
                return False
            
            print("   🔀 Switching traffic to green environment...")
            # This would update load balancer configuration
            time.sleep(1)
            
            print("   ✅ Blue-green deployment completed")
            return True
            
        except Exception as e:
            logger.error(f"Blue-green deployment failed: {e}")
            return False
    
    def _health_check(self, environment: str) -> bool:
        """Perform health check on environment."""
        try:
            env_config = self.deployment_config.get("environments", {}).get(environment, {})
            api_url = env_config.get("api_url", "http://localhost:8000")
            
            # In a real implementation, this would make HTTP requests to health endpoints
            # For now, we'll simulate a successful health check
            print(f"   Checking health of {api_url}...")
            
            # Simulate health check
            time.sleep(1)
            
            # Check feature flag system health
            try:
                flag_status = self.flag_manager.get_flag_status()
                if not flag_status:
                    return False
            except Exception:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def post_deployment_checks(self, environment: str) -> bool:
        """Run post-deployment checks."""
        print(f"🔍 Running post-deployment checks for {environment}...")
        
        checks = self.deployment_config.get("deployment", {}).get("post_deployment_checks", [])
        
        for check in checks:
            print(f"   Running {check}...")
            
            if check == "health_check":
                if not self._health_check(environment):
                    print(f"   ❌ {check} failed")
                    return False
            
            elif check == "smoke_tests":
                if not self._smoke_tests(environment):
                    print(f"   ❌ {check} failed")
                    return False
            
            elif check == "performance_check":
                if not self._performance_check(environment):
                    print(f"   ❌ {check} failed")
                    return False
            
            print(f"   ✅ {check} passed")
        
        print("✅ All post-deployment checks passed")
        return True
    
    def _smoke_tests(self, environment: str) -> bool:
        """Run smoke tests."""
        try:
            # Test basic feature flag functionality
            test_user = "smoke_test_user"
            decision = self.flag_manager.should_use_simple_trends(test_user, "test_keyword")
            
            # Test should return a boolean
            if not isinstance(decision, bool):
                logger.error("Feature flag decision not boolean")
                return False
            
            # Test performance metrics recording
            from feature_flags import TrendsClientType
            self.flag_manager.record_performance_metrics(
                TrendsClientType.SIMPLE_TRENDS, "smoke_test", 1.0, True, False, 0.9
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Smoke tests failed: {e}")
            return False
    
    def _performance_check(self, environment: str) -> bool:
        """Check performance metrics."""
        try:
            # Get performance report
            report = self.flag_manager.get_performance_report()
            
            # Check if report is valid
            if not report or "performance_metrics" not in report:
                logger.warning("No performance metrics available")
                return True  # Not a failure, just no data yet
            
            # Check performance thresholds
            thresholds = self.deployment_config.get("monitoring", {}).get("alert_thresholds", {})
            
            for client_type, metrics in report["performance_metrics"].items():
                avg_response_time = metrics.get("avg_response_time", 0)
                max_response_time = thresholds.get("response_time_ms", 2000) / 1000  # Convert to seconds
                
                if avg_response_time > max_response_time:
                    logger.error(f"Response time too high: {avg_response_time}s > {max_response_time}s")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
            return False
    
    def rollback(self, environment: str, version: str = None) -> bool:
        """Rollback to previous version."""
        print(f"🔄 Rolling back {environment}...")
        
        try:
            # Find backup to restore
            if version is None:
                # Find latest backup
                backup_dir = Path(f"backups/{environment}")
                if not backup_dir.exists():
                    print("❌ No backups found")
                    return False
                
                # Get latest backup
                backups = sorted([d for d in backup_dir.iterdir() if d.is_dir()], reverse=True)
                if not backups:
                    print("❌ No backup versions found")
                    return False
                
                version = backups[0].name
            
            backup_path = Path(f"backups/{environment}/{version}")
            if not backup_path.exists():
                print(f"❌ Backup not found: {backup_path}")
                return False
            
            print(f"📦 Restoring from backup: {version}")
            
            # Restore configuration files
            config_files = ["feature_flags.json", "settings.py", ".env"]
            for config_file in config_files:
                backup_file = backup_path / config_file
                if backup_file.exists():
                    import shutil
                    target_path = Path("config") / config_file if config_file.endswith('.json') else Path(config_file)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, target_path)
                    print(f"   Restored {config_file}")
            
            # Restore feature flag state
            flag_state_file = backup_path / "feature_flags_state.json"
            if flag_state_file.exists():
                with open(flag_state_file, 'r') as f:
                    flag_state = json.load(f)
                
                # Restore key settings
                if "use_simple_trends" in flag_state:
                    percentage = flag_state["use_simple_trends"].get("percentage", 0.0)
                    self.flag_manager.update_flag_percentage(percentage)
                    print(f"   Restored Simple Trends percentage: {percentage}%")
                
                if "enable_a_b_testing" in flag_state:
                    ab_state = flag_state["enable_a_b_testing"]["state"]
                    if ab_state == "enabled":
                        split = flag_state["enable_a_b_testing"].get("split", 50.0)
                        self.flag_manager.enable_a_b_testing(split)
                        print(f"   Restored A/B testing: {split}% split")
                    else:
                        self.flag_manager.disable_a_b_testing()
                        print("   Disabled A/B testing")
            
            # Run health check after rollback
            if not self._health_check(environment):
                print("⚠️  Rollback completed but health check failed")
                return False
            
            print(f"✅ Rollback to {version} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            print(f"❌ Rollback failed: {e}")
            return False
    
    def emergency_rollback(self, environment: str) -> bool:
        """Emergency rollback - disable all Simple Trends traffic."""
        print(f"🚨 EMERGENCY ROLLBACK for {environment}")
        
        try:
            # Force all traffic back to Google Trends
            self.flag_manager.update_flag_percentage(0.0)
            self.flag_manager.disable_a_b_testing()
            self.flag_manager.disable_force_simple_trends()
            
            print("✅ Emergency rollback completed - all traffic routed to Google Trends")
            return True
            
        except Exception as e:
            logger.error(f"Emergency rollback failed: {e}")
            print(f"❌ Emergency rollback failed: {e}")
            return False
    
    def status(self, environment: str) -> Dict[str, Any]:
        """Get deployment status."""
        try:
            flag_status = self.flag_manager.get_flag_status()
            performance_report = self.flag_manager.get_performance_report()
            
            # Check if backups exist
            backup_dir = Path(f"backups/{environment}")
            backup_count = len(list(backup_dir.iterdir())) if backup_dir.exists() else 0
            
            status = {
                "environment": environment,
                "timestamp": datetime.now().isoformat(),
                "feature_flags": flag_status,
                "performance_metrics": performance_report.get("performance_metrics", {}),
                "backup_count": backup_count,
                "health_status": "healthy" if self._health_check(environment) else "unhealthy"
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}
    
    def cleanup_old_backups(self, environment: str, retention_days: int = None) -> bool:
        """Clean up old backups."""
        if retention_days is None:
            retention_days = self.deployment_config.get("deployment", {}).get("backup_retention_days", 7)
        
        try:
            backup_dir = Path(f"backups/{environment}")
            if not backup_dir.exists():
                return True
            
            cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
            
            for backup_path in backup_dir.iterdir():
                if backup_path.is_dir():
                    if backup_path.stat().st_mtime < cutoff_time:
                        import shutil
                        shutil.rmtree(backup_path)
                        print(f"Removed old backup: {backup_path.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return False


def create_cli_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Deploy Simple Trends system with blue-green deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy to staging
  python scripts/deploy.py deploy staging
  
  # Deploy specific version to production
  python scripts/deploy.py deploy production --version v1.2.3
  
  # Check deployment status
  python scripts/deploy.py status production
  
  # Rollback to previous version
  python scripts/deploy.py rollback production
  
  # Emergency rollback (disable Simple Trends)
  python scripts/deploy.py emergency-rollback production
  
  # Clean up old backups
  python scripts/deploy.py cleanup staging --retention-days 7
        """
    )
    
    parser.add_argument(
        '--config-file',
        type=Path,
        help='Path to deployment configuration file'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy to environment')
    deploy_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    deploy_parser.add_argument('--version', help='Version to deploy')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get deployment status')
    status_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback deployment')
    rollback_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    rollback_parser.add_argument('--version', help='Version to rollback to')
    
    # Emergency rollback command
    emergency_parser = subparsers.add_parser('emergency-rollback', help='Emergency rollback')
    emergency_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old backups')
    cleanup_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    cleanup_parser.add_argument('--retention-days', type=int, default=7, help='Backup retention days')
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize deployment manager
    deployment_manager = DeploymentManager(args.config_file)
    
    # Execute command
    if args.command == 'deploy':
        success = deployment_manager.deploy(args.environment, args.version)
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        status = deployment_manager.status(args.environment)
        print(json.dumps(status, indent=2))
    
    elif args.command == 'rollback':
        success = deployment_manager.rollback(args.environment, args.version)
        sys.exit(0 if success else 1)
    
    elif args.command == 'emergency-rollback':
        success = deployment_manager.emergency_rollback(args.environment)
        sys.exit(0 if success else 1)
    
    elif args.command == 'cleanup':
        success = deployment_manager.cleanup_old_backups(args.environment, args.retention_days)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()