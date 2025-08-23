#!/usr/bin/env python3
"""Feature Flag Management CLI Script.

This script provides a command-line interface for managing feature flags
during the Simple Trends migration.
"""

import sys
import os
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import directly from the data module to avoid MCP dependency
sys.path.insert(0, str(project_root / "src" / "kdp_strategist" / "data"))

from feature_flags import FeatureFlagManager, FeatureFlagState, TrendsClientType

logger = logging.getLogger(__name__)


class FeatureFlagConfigManager:
    """Manages feature flag configuration through CLI and programmatic interfaces."""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config/feature_flags.json")
        self.flag_manager = FeatureFlagManager(self.config_file)
    
    def set_simple_trends_percentage(self, percentage: float) -> bool:
        """Set the percentage for Simple Trends rollout."""
        try:
            self.flag_manager.update_flag_percentage(percentage)
            print(f"✅ Updated Simple Trends rollout to {percentage}%")
            return True
        except Exception as e:
            print(f"❌ Failed to update percentage: {e}")
            return False
    
    def enable_ab_testing(self, split: float = 50.0) -> bool:
        """Enable A/B testing with specified split."""
        try:
            self.flag_manager.enable_a_b_testing(split)
            print(f"✅ Enabled A/B testing with {split}% for Simple Trends")
            return True
        except Exception as e:
            print(f"❌ Failed to enable A/B testing: {e}")
            return False
    
    def disable_ab_testing(self) -> bool:
        """Disable A/B testing."""
        try:
            self.flag_manager.disable_a_b_testing()
            print("✅ Disabled A/B testing")
            return True
        except Exception as e:
            print(f"❌ Failed to disable A/B testing: {e}")
            return False
    
    def enable_force_simple_trends(self) -> bool:
        """Enable emergency switch to force all traffic to Simple Trends."""
        try:
            self.flag_manager.enable_force_simple_trends()
            print("🚨 EMERGENCY: Forced all traffic to Simple Trends")
            return True
        except Exception as e:
            print(f"❌ Failed to enable force flag: {e}")
            return False
    
    def disable_force_simple_trends(self) -> bool:
        """Disable emergency force flag."""
        try:
            self.flag_manager.disable_force_simple_trends()
            print("✅ Disabled force Simple Trends flag")
            return True
        except Exception as e:
            print(f"❌ Failed to disable force flag: {e}")
            return False
    
    def add_user_override(self, flag_name: str, user_id: str, enabled: bool) -> bool:
        """Add user-specific override."""
        try:
            self.flag_manager.add_user_override(flag_name, user_id, enabled)
            action = "enabled" if enabled else "disabled"
            print(f"✅ {action.capitalize()} {flag_name} for user {user_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to add user override: {e}")
            return False
    
    def show_status(self):
        """Display current feature flag status."""
        try:
            status = self.flag_manager.get_flag_status()
            
            print("\n🏁 Feature Flag Status")
            print("=" * 50)
            
            # Simple Trends rollout
            simple_flag = status["use_simple_trends"]
            print(f"\n📊 Simple Trends Rollout:")
            print(f"   State: {simple_flag['state']}")
            if simple_flag['state'] == 'percentage':
                print(f"   Percentage: {simple_flag['percentage']}%")
            print(f"   User Overrides: {simple_flag['enabled_users']} enabled, {simple_flag['disabled_users']} disabled")
            
            # A/B Testing
            ab_flag = status["enable_a_b_testing"]
            print(f"\n🧪 A/B Testing:")
            print(f"   State: {ab_flag['state']}")
            if ab_flag['state'] == 'enabled':
                print(f"   Split: {ab_flag['split']}% Simple Trends, {100-ab_flag['split']}% Google Trends")
            print(f"   User Overrides: {ab_flag['enabled_users']} enabled, {ab_flag['disabled_users']} disabled")
            
            # Force flag
            force_flag = status["force_simple_trends"]
            print(f"\n🚨 Emergency Force Flag:")
            print(f"   State: {force_flag['state']}")
            if force_flag['state'] == 'enabled':
                print("   ⚠️  ALL TRAFFIC FORCED TO SIMPLE TRENDS")
            print(f"   User Overrides: {force_flag['enabled_users']} enabled, {force_flag['disabled_users']} disabled")
            
            # Performance monitoring
            perf_flag = status["performance_monitoring"]
            print(f"\n📈 Performance Monitoring:")
            print(f"   State: {perf_flag['state']}")
            
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
    
    def show_performance_report(self):
        """Display performance report."""
        try:
            report = self.flag_manager.get_performance_report()
            
            print("\n📈 Performance Report")
            print("=" * 50)
            print(f"Generated: {report['timestamp']}")
            
            metrics = report.get('performance_metrics', {})
            
            if not metrics:
                print("\n📊 No performance data available yet")
                return
            
            for client_type, data in metrics.items():
                print(f"\n🔧 {client_type.replace('_', ' ').title()}:")
                print(f"   Keywords Analyzed: {data['total_keywords']}")
                print(f"   Total Requests: {data['total_requests']}")
                print(f"   Total Errors: {data['total_errors']}")
                print(f"   Avg Response Time: {data['avg_response_time']:.2f}s")
                print(f"   Avg Success Rate: {data['avg_success_rate']:.1f}%")
                print(f"   Avg Cache Hit Rate: {data['avg_cache_hit_rate']:.1f}%")
                print(f"   Avg Confidence Level: {data['avg_confidence_level']:.1f}%")
            
            # Compare performance if both clients have data
            if len(metrics) > 1:
                print(f"\n⚖️  Performance Comparison:")
                clients = list(metrics.keys())
                client_a, client_b = clients[0], clients[1]
                
                time_diff = metrics[client_a]['avg_response_time'] - metrics[client_b]['avg_response_time']
                faster_client = client_a if time_diff < 0 else client_b
                print(f"   Faster Client: {faster_client.replace('_', ' ').title()} ({abs(time_diff):.2f}s faster)")
                
                success_diff = metrics[client_a]['avg_success_rate'] - metrics[client_b]['avg_success_rate']
                better_client = client_a if success_diff > 0 else client_b
                print(f"   Higher Success Rate: {better_client.replace('_', ' ').title()} ({abs(success_diff):.1f}% better)")
                
        except Exception as e:
            print(f"❌ Failed to get performance report: {e}")


def create_cli_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Manage feature flags for Simple Trends migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current status
  python scripts/manage_feature_flags.py status
  
  # Set Simple Trends to 25% rollout
  python scripts/manage_feature_flags.py set-percentage 25
  
  # Enable A/B testing with 50/50 split
  python scripts/manage_feature_flags.py enable-ab-test
  
  # Enable A/B testing with 30% Simple Trends
  python scripts/manage_feature_flags.py enable-ab-test --split 30
  
  # Emergency: Force all traffic to Simple Trends
  python scripts/manage_feature_flags.py force-simple-trends
  
  # Add user override
  python scripts/manage_feature_flags.py add-user-override use_simple_trends user123 --enable
  
  # Show performance report
  python scripts/manage_feature_flags.py performance
        """
    )
    
    parser.add_argument(
        '--config-file',
        type=Path,
        help='Path to feature flag configuration file'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show current feature flag status')
    
    # Set percentage command
    percentage_parser = subparsers.add_parser('set-percentage', help='Set Simple Trends rollout percentage')
    percentage_parser.add_argument('percentage', type=float, help='Percentage (0-100)')
    
    # A/B testing commands
    ab_enable_parser = subparsers.add_parser('enable-ab-test', help='Enable A/B testing')
    ab_enable_parser.add_argument('--split', type=float, default=50.0, help='Percentage for Simple Trends (default: 50)')
    
    subparsers.add_parser('disable-ab-test', help='Disable A/B testing')
    
    # Force commands
    subparsers.add_parser('force-simple-trends', help='Emergency: Force all traffic to Simple Trends')
    subparsers.add_parser('unforce-simple-trends', help='Disable emergency force flag')
    
    # User override command
    user_parser = subparsers.add_parser('add-user-override', help='Add user-specific override')
    user_parser.add_argument('flag_name', help='Flag name (use_simple_trends, enable_a_b_testing, force_simple_trends)')
    user_parser.add_argument('user_id', help='User ID')
    user_parser.add_argument('--enable', action='store_true', help='Enable for user')
    user_parser.add_argument('--disable', action='store_true', help='Disable for user')
    
    # Performance command
    subparsers.add_parser('performance', help='Show performance report')
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize configuration manager
    config_manager = FeatureFlagConfigManager(args.config_file)
    
    # Execute command
    if args.command == 'status':
        config_manager.show_status()
    
    elif args.command == 'set-percentage':
        config_manager.set_simple_trends_percentage(args.percentage)
    
    elif args.command == 'enable-ab-test':
        config_manager.enable_ab_testing(args.split)
    
    elif args.command == 'disable-ab-test':
        config_manager.disable_ab_testing()
    
    elif args.command == 'force-simple-trends':
        config_manager.enable_force_simple_trends()
    
    elif args.command == 'unforce-simple-trends':
        config_manager.disable_force_simple_trends()
    
    elif args.command == 'add-user-override':
        if args.enable and args.disable:
            print("❌ Cannot specify both --enable and --disable")
            return
        if not args.enable and not args.disable:
            print("❌ Must specify either --enable or --disable")
            return
        
        config_manager.add_user_override(args.flag_name, args.user_id, args.enable)
    
    elif args.command == 'performance':
        config_manager.show_performance_report()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()