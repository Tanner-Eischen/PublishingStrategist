#!/usr/bin/env python3
"""
Production Monitoring Startup Script

This script starts all production monitoring components for the KDP Strategist system.
"""

import asyncio
import argparse
import json
import logging
import signal
import sys
from pathlib import Path
from typing import List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kdp_strategist.data.production_monitoring_dashboard import ProductionMonitoringDashboard
from kdp_strategist.data.log_aggregation_system import LogAggregator, LogMonitoringService
from kdp_strategist.data.automated_incident_response import AutomatedIncidentResponse
from kdp_strategist.data.simple_trends_monitoring import SimpleTrendsMonitor
from config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/production_monitoring.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ProductionMonitoringManager:
    """Manages all production monitoring components."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/production_monitoring.json"
        self.config = self._load_config()
        
        # Initialize components
        self.trends_config = get_settings()
        self.trends_monitor = SimpleTrendsMonitor(self.trends_config)
        self.dashboard = ProductionMonitoringDashboard(
            self.trends_config, 
            self.trends_monitor
        )
        self.log_aggregator = LogAggregator(self.trends_config)
        self.log_monitoring = LogMonitoringService(
            self.trends_config, 
            self.log_aggregator
        )
        
        # Load incident response config
        incident_config = self._load_incident_config()
        self.incident_response = AutomatedIncidentResponse(incident_config)
        
        # Track running components
        self.running_components: List[str] = []
        self.shutdown_event = asyncio.Event()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self) -> dict:
        """Load monitoring configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded monitoring configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return {}
    
    def _load_incident_config(self) -> dict:
        """Load incident response configuration."""
        try:
            with open("config/incident_response.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Incident response config not found, using defaults")
            return {}
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()
    
    async def start_all_components(self):
        """Start all monitoring components."""
        logger.info("Starting production monitoring system...")
        
        try:
            # Start dashboard monitoring
            if self.config.get("monitoring", {}).get("enabled", True):
                await self.dashboard.start_monitoring()
                self.running_components.append("dashboard")
                logger.info("✓ Dashboard monitoring started")
            
            # Start log monitoring
            if self.config.get("log_monitoring", {}).get("enabled", True):
                self.log_monitoring.start_monitoring()
                self.running_components.append("log_monitoring")
                logger.info("✓ Log monitoring started")
            
            # Start incident response
            if self.config.get("automated_responses", {}).get("enabled", True):
                await self.incident_response.start_monitoring()
                self.running_components.append("incident_response")
                logger.info("✓ Incident response started")
            
            # Parse existing log files
            await self._parse_existing_logs()
            
            logger.info("🚀 All monitoring components started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring components: {e}")
            await self.stop_all_components()
            raise
    
    async def _parse_existing_logs(self):
        """Parse existing log files on startup."""
        try:
            log_dirs = self.config.get("log_monitoring", {}).get("log_directories", ["logs", "."])
            total_entries = 0
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if log_path.exists():
                    entries = self.log_aggregator.parse_log_directory(log_path)
                    total_entries += entries
                    logger.info(f"Parsed {entries} log entries from {log_path}")
            
            logger.info(f"✓ Parsed {total_entries} total log entries")
            
        except Exception as e:
            logger.error(f"Failed to parse existing logs: {e}")
    
    async def stop_all_components(self):
        """Stop all monitoring components."""
        logger.info("Stopping production monitoring system...")
        
        # Stop components in reverse order
        if "incident_response" in self.running_components:
            try:
                await self.incident_response.stop_monitoring()
                logger.info("✓ Incident response stopped")
            except Exception as e:
                logger.error(f"Error stopping incident response: {e}")
        
        if "log_monitoring" in self.running_components:
            try:
                self.log_monitoring.stop_monitoring()
                logger.info("✓ Log monitoring stopped")
            except Exception as e:
                logger.error(f"Error stopping log monitoring: {e}")
        
        if "dashboard" in self.running_components:
            try:
                await self.dashboard.stop_monitoring()
                logger.info("✓ Dashboard monitoring stopped")
            except Exception as e:
                logger.error(f"Error stopping dashboard: {e}")
        
        self.running_components.clear()
        logger.info("🛑 All monitoring components stopped")
    
    async def run_monitoring_loop(self):
        """Main monitoring loop."""
        try:
            await self.start_all_components()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
        finally:
            await self.stop_all_components()
    
    def get_status(self) -> dict:
        """Get current monitoring status."""
        return {
            "running_components": self.running_components,
            "dashboard_active": "dashboard" in self.running_components,
            "log_monitoring_active": "log_monitoring" in self.running_components,
            "incident_response_active": "incident_response" in self.running_components,
            "total_log_entries": len(self.log_aggregator.log_entries),
            "active_alerts": len([
                alert for alert in self.dashboard.active_alerts.values()
                if not alert.resolved
            ]),
            "config_loaded": bool(self.config)
        }
    
    async def health_check(self) -> dict:
        """Perform comprehensive health check."""
        health_status = {
            "overall_status": "healthy",
            "components": {},
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Check dashboard
        try:
            if "dashboard" in self.running_components:
                dashboard_health = await self.dashboard._perform_comprehensive_health_check()
                health_status["components"]["dashboard"] = {
                    "status": "healthy",
                    "details": dashboard_health
                }
            else:
                health_status["components"]["dashboard"] = {
                    "status": "stopped",
                    "details": "Dashboard monitoring not running"
                }
        except Exception as e:
            health_status["components"]["dashboard"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        # Check log monitoring
        try:
            if "log_monitoring" in self.running_components:
                log_status = self.log_monitoring.get_monitoring_status()
                health_status["components"]["log_monitoring"] = {
                    "status": "healthy",
                    "details": log_status
                }
            else:
                health_status["components"]["log_monitoring"] = {
                    "status": "stopped",
                    "details": "Log monitoring not running"
                }
        except Exception as e:
            health_status["components"]["log_monitoring"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        # Check incident response
        try:
            if "incident_response" in self.running_components:
                incident_summary = self.incident_response.get_incident_summary()
                health_status["components"]["incident_response"] = {
                    "status": "healthy",
                    "details": incident_summary
                }
            else:
                health_status["components"]["incident_response"] = {
                    "status": "stopped",
                    "details": "Incident response not running"
                }
        except Exception as e:
            health_status["components"]["incident_response"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        return health_status


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="KDP Strategist Production Monitoring")
    parser.add_argument("--config", help="Path to monitoring config file")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--health", action="store_true", help="Run health check and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    # Create monitoring manager
    manager = ProductionMonitoringManager(args.config)
    
    if args.status:
        # Show status and exit
        status = manager.get_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.health:
        # Run health check and exit
        health = await manager.health_check()
        print(json.dumps(health, indent=2))
        return
    
    # Run monitoring system
    try:
        if args.daemon:
            logger.info("Starting monitoring system in daemon mode")
        else:
            logger.info("Starting monitoring system in foreground mode")
        
        await manager.run_monitoring_loop()
        
    except Exception as e:
        logger.error(f"Failed to run monitoring system: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run the monitoring system
    asyncio.run(main())