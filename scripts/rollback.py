#!/usr/bin/env python3
"""Rollback Script for Simple Trends System.

This script provides comprehensive rollback capabilities including
emergency rollback procedures and automated rollback triggers.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "kdp_strategist" / "data"))

from feature_flags import FeatureFlagManager

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages rollback operations for Simple Trends system."""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config/deployment.json")
        self.flag_manager = FeatureFlagManager()
        self.rollback_config = self._load_rollback_config()
        
        logger.info("RollbackManager initialized")
    
    def _load_rollback_config(self) -> Dict[str, Any]:
        """Load rollback configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                return config.get("rollback", {})
            except Exception as e:
                logger.warning(f"Failed to load rollback config: {e}")
        
        # Default rollback configuration
        return {
            "automatic_rollback": {
                "enabled": True,
                "triggers": [
                    "health_check_failure",
                    "high_error_rate",
                    "performance_degradation"
                ],
                "cooldown_minutes": 15
            },
            "manual_rollback": {
                "confirmation_required": True,
                "backup_before_rollback": True
            },
            "emergency_rollback": {
                "disable_simple_trends": True,
                "force_google_trends": True,
                "notify_immediately": True
            }
        }
    
    def check_rollback_triggers(self, environment: str) -> List[str]:
        """Check if any automatic rollback triggers are active."""
        triggers = []
        
        try:
            # Check health status
            if not self._check_health(environment):
                triggers.append("health_check_failure")
            
            # Check error rate
            if self._check_error_rate(environment):
                triggers.append("high_error_rate")
            
            # Check performance degradation
            if self._check_performance_degradation(environment):
                triggers.append("performance_degradation")
            
            # Check feature flag system health
            if not self._check_feature_flag_health():
                triggers.append("feature_flag_failure")
            
        except Exception as e:
            logger.error(f"Error checking rollback triggers: {e}")
            triggers.append("monitoring_failure")
        
        return triggers
    
    def _check_health(self, environment: str) -> bool:
        """Check if the environment is healthy."""
        try:
            # In a real implementation, this would check actual health endpoints
            # For now, we'll simulate health checks
            
            # Check if feature flag system is responding
            flag_status = self.flag_manager.get_flag_status()
            if not flag_status:
                return False
            
            # Check performance metrics
            performance_report = self.flag_manager.get_performance_report()
            if not performance_report:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def _check_error_rate(self, environment: str) -> bool:
        """Check if error rate is too high."""
        try:
            performance_report = self.flag_manager.get_performance_report()
            
            if "performance_metrics" not in performance_report:
                return False
            
            for client_type, metrics in performance_report["performance_metrics"].items():
                success_rate = metrics.get("success_rate", 1.0)
                if success_rate < 0.95:  # Less than 95% success rate
                    logger.warning(f"High error rate detected for {client_type}: {1-success_rate:.2%}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error rate check failed: {e}")
            return True  # Assume high error rate if we can't check
    
    def _check_performance_degradation(self, environment: str) -> bool:
        """Check if performance has degraded significantly."""
        try:
            performance_report = self.flag_manager.get_performance_report()
            
            if "performance_metrics" not in performance_report:
                return False
            
            for client_type, metrics in performance_report["performance_metrics"].items():
                avg_response_time = metrics.get("avg_response_time", 0)
                if avg_response_time > 2.0:  # More than 2 seconds
                    logger.warning(f"Performance degradation detected for {client_type}: {avg_response_time:.2f}s")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
            return True  # Assume degradation if we can't check
    
    def _check_feature_flag_health(self) -> bool:
        """Check if feature flag system is healthy."""
        try:
            # Test basic feature flag operations
            test_user = "health_check_user"
            decision = self.flag_manager.should_use_simple_trends(test_user, "health_check")
            
            if not isinstance(decision, bool):
                return False
            
            # Check if we can get status
            status = self.flag_manager.get_flag_status()
            if not status:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Feature flag health check failed: {e}")
            return False
    
    def should_auto_rollback(self, environment: str) -> bool:
        """Check if automatic rollback should be triggered."""
        config = self.rollback_config.get("automatic_rollback", {})
        
        if not config.get("enabled", False):
            return False
        
        # Check cooldown period
        if self._is_in_cooldown(environment):
            logger.info("Rollback is in cooldown period")
            return False
        
        # Check triggers
        active_triggers = self.check_rollback_triggers(environment)
        configured_triggers = config.get("triggers", [])
        
        # If any configured trigger is active, rollback should be triggered
        for trigger in active_triggers:
            if trigger in configured_triggers:
                logger.warning(f"Automatic rollback trigger activated: {trigger}")
                return True
        
        return False
    
    def _is_in_cooldown(self, environment: str) -> bool:
        """Check if rollback is in cooldown period."""
        cooldown_file = Path(f"backups/{environment}/last_rollback.json")
        
        if not cooldown_file.exists():
            return False
        
        try:
            with open(cooldown_file, 'r') as f:
                data = json.load(f)
            
            last_rollback = datetime.fromisoformat(data["timestamp"])
            cooldown_minutes = self.rollback_config.get("automatic_rollback", {}).get("cooldown_minutes", 15)
            cooldown_until = last_rollback + timedelta(minutes=cooldown_minutes)
            
            return datetime.now() < cooldown_until
            
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return False
    
    def _record_rollback(self, environment: str, rollback_type: str, reason: str):
        """Record rollback event."""
        backup_dir = Path(f"backups/{environment}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        rollback_record = {
            "timestamp": datetime.now().isoformat(),
            "type": rollback_type,
            "reason": reason,
            "environment": environment
        }
        
        # Record in last_rollback.json for cooldown tracking
        with open(backup_dir / "last_rollback.json", 'w') as f:
            json.dump(rollback_record, f, indent=2)
        
        # Append to rollback history
        history_file = backup_dir / "rollback_history.json"
        history = []
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except Exception:
                history = []
        
        history.append(rollback_record)
        
        # Keep only last 50 rollback records
        history = history[-50:]
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        logger.info(f"Recorded rollback: {rollback_type} - {reason}")
    
    def emergency_rollback(self, environment: str, reason: str = "Emergency rollback") -> bool:
        """Perform emergency rollback - immediately disable Simple Trends."""
        print(f"🚨 EMERGENCY ROLLBACK INITIATED for {environment}")
        print(f"Reason: {reason}")
        
        try:
            # Record the emergency rollback
            self._record_rollback(environment, "emergency", reason)
            
            # Immediately disable Simple Trends
            print("   Disabling Simple Trends system...")
            self.flag_manager.update_flag_percentage(0.0)
            self.flag_manager.disable_a_b_testing()
            self.flag_manager.disable_force_simple_trends()
            
            # Verify the rollback
            status = self.flag_manager.get_flag_status()
            if status and status.get("use_simple_trends", {}).get("percentage", 100) == 0:
                print("✅ Emergency rollback completed successfully")
                print("   All traffic is now routed to Google Trends")
                
                # Send notifications
                self._send_rollback_notification(environment, "emergency", reason)
                
                return True
            else:
                print("❌ Emergency rollback verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Emergency rollback failed: {e}")
            print(f"❌ Emergency rollback failed: {e}")
            return False
    
    def gradual_rollback(self, environment: str, reason: str = "Gradual rollback") -> bool:
        """Perform gradual rollback by reducing Simple Trends traffic."""
        print(f"🔄 GRADUAL ROLLBACK INITIATED for {environment}")
        print(f"Reason: {reason}")
        
        try:
            # Record the rollback
            self._record_rollback(environment, "gradual", reason)
            
            # Get current percentage
            status = self.flag_manager.get_flag_status()
            current_percentage = status.get("use_simple_trends", {}).get("percentage", 0)
            
            print(f"   Current Simple Trends traffic: {current_percentage}%")
            
            # Gradually reduce traffic
            rollback_steps = [50, 25, 10, 0]
            
            for target_percentage in rollback_steps:
                if current_percentage <= target_percentage:
                    continue
                
                print(f"   Reducing Simple Trends traffic to {target_percentage}%...")
                self.flag_manager.update_flag_percentage(target_percentage)
                
                # Wait and check health
                time.sleep(30)
                
                if not self._check_health(environment):
                    print(f"   Health check failed at {target_percentage}%, continuing rollback...")
                    continue
                else:
                    print(f"   System stable at {target_percentage}%")
                    if target_percentage > 0:
                        print("   Rollback paused - system appears stable")
                        return True
            
            print("✅ Gradual rollback completed - all traffic routed to Google Trends")
            
            # Send notifications
            self._send_rollback_notification(environment, "gradual", reason)
            
            return True
            
        except Exception as e:
            logger.error(f"Gradual rollback failed: {e}")
            print(f"❌ Gradual rollback failed: {e}")
            return False
    
    def version_rollback(self, environment: str, target_version: str = None) -> bool:
        """Rollback to a specific version."""
        print(f"🔄 VERSION ROLLBACK INITIATED for {environment}")
        
        try:
            # Find target version
            if target_version is None:
                target_version = self._find_last_stable_version(environment)
                if not target_version:
                    print("❌ No stable version found for rollback")
                    return False
            
            print(f"   Rolling back to version: {target_version}")
            
            # Record the rollback
            self._record_rollback(environment, "version", f"Rollback to {target_version}")
            
            # Use deployment script for version rollback
            deploy_script = Path("scripts/deploy.py")
            if deploy_script.exists():
                result = subprocess.run([
                    sys.executable, str(deploy_script),
                    "rollback", environment, "--version", target_version
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ Version rollback completed successfully")
                    
                    # Send notifications
                    self._send_rollback_notification(environment, "version", f"Rollback to {target_version}")
                    
                    return True
                else:
                    print(f"❌ Version rollback failed: {result.stderr}")
                    return False
            else:
                print("❌ Deployment script not found")
                return False
                
        except Exception as e:
            logger.error(f"Version rollback failed: {e}")
            print(f"❌ Version rollback failed: {e}")
            return False
    
    def _find_last_stable_version(self, environment: str) -> Optional[str]:
        """Find the last stable version for rollback."""
        backup_dir = Path(f"backups/{environment}")
        
        if not backup_dir.exists():
            return None
        
        # Look for backup directories (versions)
        versions = []
        for version_dir in backup_dir.iterdir():
            if version_dir.is_dir() and version_dir.name != "rollback_history.json":
                # Check if this version has a successful deployment record
                metadata_file = version_dir / "backup_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        versions.append((version_dir.name, metadata.get("timestamp", "")))
                    except Exception:
                        continue
        
        if not versions:
            return None
        
        # Sort by timestamp and return the most recent
        versions.sort(key=lambda x: x[1], reverse=True)
        return versions[0][0]
    
    def _send_rollback_notification(self, environment: str, rollback_type: str, reason: str):
        """Send rollback notification."""
        try:
            # In a real implementation, this would send notifications via email, Slack, etc.
            notification = {
                "type": "rollback",
                "environment": environment,
                "rollback_type": rollback_type,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            logger.info(f"Rollback notification: {notification}")
            
            # Save notification to file for now
            notifications_dir = Path("logs/notifications")
            notifications_dir.mkdir(parents=True, exist_ok=True)
            
            notification_file = notifications_dir / f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(notification_file, 'w') as f:
                json.dump(notification, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to send rollback notification: {e}")
    
    def auto_rollback_monitor(self, environment: str, check_interval: int = 60) -> bool:
        """Monitor system and trigger automatic rollback if needed."""
        print(f"🔍 Starting automatic rollback monitoring for {environment}")
        print(f"   Check interval: {check_interval} seconds")
        
        try:
            while True:
                if self.should_auto_rollback(environment):
                    triggers = self.check_rollback_triggers(environment)
                    reason = f"Automatic rollback triggered by: {', '.join(triggers)}"
                    
                    print(f"🚨 Automatic rollback triggered: {reason}")
                    
                    # Perform gradual rollback first
                    if self.gradual_rollback(environment, reason):
                        print("✅ Automatic rollback completed successfully")
                        return True
                    else:
                        # If gradual rollback fails, try emergency rollback
                        print("⚠️  Gradual rollback failed, attempting emergency rollback...")
                        return self.emergency_rollback(environment, f"Emergency after failed gradual rollback: {reason}")
                
                # Wait before next check
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            return True
        except Exception as e:
            logger.error(f"Auto rollback monitoring failed: {e}")
            print(f"❌ Monitoring failed: {e}")
            return False
    
    def rollback_status(self, environment: str) -> Dict[str, Any]:
        """Get rollback status and history."""
        try:
            # Check current triggers
            active_triggers = self.check_rollback_triggers(environment)
            
            # Get rollback history
            history_file = Path(f"backups/{environment}/rollback_history.json")
            history = []
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            
            # Check cooldown status
            in_cooldown = self._is_in_cooldown(environment)
            
            # Get current feature flag status
            flag_status = self.flag_manager.get_flag_status()
            
            status = {
                "environment": environment,
                "timestamp": datetime.now().isoformat(),
                "active_triggers": active_triggers,
                "should_auto_rollback": self.should_auto_rollback(environment),
                "in_cooldown": in_cooldown,
                "rollback_history": history[-10:],  # Last 10 rollbacks
                "current_feature_flags": flag_status,
                "health_status": {
                    "overall_health": self._check_health(environment),
                    "high_error_rate": self._check_error_rate(environment),
                    "performance_degradation": self._check_performance_degradation(environment),
                    "feature_flag_health": self._check_feature_flag_health()
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get rollback status: {e}")
            return {"error": str(e)}


def create_cli_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Rollback management for Simple Trends system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Emergency rollback (immediate)
  python scripts/rollback.py emergency production "Critical system failure"
  
  # Gradual rollback (step by step)
  python scripts/rollback.py gradual production "Performance degradation"
  
  # Version rollback
  python scripts/rollback.py version production --target-version 20240115_143022
  
  # Check rollback status
  python scripts/rollback.py status production
  
  # Start automatic monitoring
  python scripts/rollback.py monitor production --interval 60
        """
    )
    
    parser.add_argument(
        '--config-file',
        type=Path,
        help='Path to deployment configuration file'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Emergency rollback command
    emergency_parser = subparsers.add_parser('emergency', help='Emergency rollback (immediate)')
    emergency_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    emergency_parser.add_argument('reason', nargs='?', default='Emergency rollback', help='Reason for rollback')
    
    # Gradual rollback command
    gradual_parser = subparsers.add_parser('gradual', help='Gradual rollback (step by step)')
    gradual_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    gradual_parser.add_argument('reason', nargs='?', default='Gradual rollback', help='Reason for rollback')
    
    # Version rollback command
    version_parser = subparsers.add_parser('version', help='Rollback to specific version')
    version_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    version_parser.add_argument('--target-version', help='Target version to rollback to')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get rollback status')
    status_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start automatic rollback monitoring')
    monitor_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    monitor_parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize rollback manager
    rollback_manager = RollbackManager(args.config_file)
    
    # Execute command
    if args.command == 'emergency':
        success = rollback_manager.emergency_rollback(args.environment, args.reason)
        sys.exit(0 if success else 1)
    
    elif args.command == 'gradual':
        success = rollback_manager.gradual_rollback(args.environment, args.reason)
        sys.exit(0 if success else 1)
    
    elif args.command == 'version':
        success = rollback_manager.version_rollback(args.environment, args.target_version)
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        status = rollback_manager.rollback_status(args.environment)
        print(json.dumps(status, indent=2))
    
    elif args.command == 'monitor':
        success = rollback_manager.auto_rollback_monitor(args.environment, args.interval)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()