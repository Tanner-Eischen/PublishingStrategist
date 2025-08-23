"""Feature Flag Management API Router.

This module provides REST API endpoints for managing feature flags
during the Simple Trends migration.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from src.kdp_strategist.data.feature_flags import (
    FeatureFlagManager, 
    get_feature_flag_manager,
    TrendsClientType
)
from src.kdp_strategist.data.feature_flag_config import FeatureFlagConfigManager
from src.kdp_strategist.data.feature_flag_monitoring import (
    FeatureFlagMonitor,
    create_monitoring_dashboard_html
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances
_flag_manager: Optional[FeatureFlagManager] = None
_config_manager: Optional[FeatureFlagConfigManager] = None
_monitor: Optional[FeatureFlagMonitor] = None


def get_flag_manager() -> FeatureFlagManager:
    """Get global feature flag manager instance."""
    global _flag_manager
    if _flag_manager is None:
        _flag_manager = get_feature_flag_manager()
    return _flag_manager


def get_config_manager() -> FeatureFlagConfigManager:
    """Get global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = FeatureFlagConfigManager()
    return _config_manager


def get_monitor() -> FeatureFlagMonitor:
    """Get global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = FeatureFlagMonitor(get_flag_manager())
        _monitor.start_monitoring()
    return _monitor


# Pydantic models for request/response
class PercentageUpdateRequest(BaseModel):
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage for Simple Trends rollout (0-100)")


class ABTestRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable A/B testing")
    split_percentage: float = Field(50.0, ge=0.0, le=100.0, description="Percentage for Simple Trends in A/B test")


class UserOverrideRequest(BaseModel):
    flag_name: str = Field(..., description="Flag name (use_simple_trends, enable_a_b_testing, force_simple_trends)")
    user_id: str = Field(..., description="User ID")
    enabled: bool = Field(..., description="Enable or disable for user")


class FeatureFlagStatusResponse(BaseModel):
    use_simple_trends: Dict[str, Any]
    enable_a_b_testing: Dict[str, Any]
    force_simple_trends: Dict[str, Any]
    performance_monitoring: Dict[str, Any]


# Feature Flag Status Endpoints
@router.get("/status", response_model=FeatureFlagStatusResponse)
async def get_feature_flag_status():
    """Get current status of all feature flags."""
    try:
        flag_manager = get_flag_manager()
        status = flag_manager.get_flag_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get feature flag status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/performance")
async def get_performance_report():
    """Get comprehensive performance report."""
    try:
        flag_manager = get_flag_manager()
        report = flag_manager.get_performance_report()
        return report
    except Exception as e:
        logger.error(f"Failed to get performance report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance report: {str(e)}")


# Feature Flag Configuration Endpoints
@router.post("/simple-trends/percentage")
async def update_simple_trends_percentage(request: PercentageUpdateRequest):
    """Update the percentage for Simple Trends rollout."""
    try:
        flag_manager = get_flag_manager()
        flag_manager.update_flag_percentage(request.percentage)
        
        return {
            "success": True,
            "message": f"Updated Simple Trends rollout to {request.percentage}%",
            "percentage": request.percentage,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to update percentage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update percentage: {str(e)}")


@router.post("/ab-testing")
async def configure_ab_testing(request: ABTestRequest):
    """Enable or disable A/B testing."""
    try:
        flag_manager = get_flag_manager()
        
        if request.enabled:
            flag_manager.enable_a_b_testing(request.split_percentage)
            message = f"Enabled A/B testing with {request.split_percentage}% for Simple Trends"
        else:
            flag_manager.disable_a_b_testing()
            message = "Disabled A/B testing"
        
        return {
            "success": True,
            "message": message,
            "enabled": request.enabled,
            "split_percentage": request.split_percentage if request.enabled else None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to configure A/B testing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to configure A/B testing: {str(e)}")


@router.post("/force-simple-trends")
async def toggle_force_simple_trends(enabled: bool = Body(..., embed=True)):
    """Enable or disable emergency force flag for Simple Trends."""
    try:
        flag_manager = get_flag_manager()
        
        if enabled:
            flag_manager.enable_force_simple_trends()
            message = "🚨 EMERGENCY: Forced all traffic to Simple Trends"
            logger.warning(message)
        else:
            flag_manager.disable_force_simple_trends()
            message = "Disabled force Simple Trends flag"
            logger.info(message)
        
        return {
            "success": True,
            "message": message,
            "enabled": enabled,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to toggle force flag: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle force flag: {str(e)}")


@router.post("/user-override")
async def add_user_override(request: UserOverrideRequest):
    """Add user-specific override for a flag."""
    try:
        flag_manager = get_flag_manager()
        flag_manager.add_user_override(request.flag_name, request.user_id, request.enabled)
        
        action = "enabled" if request.enabled else "disabled"
        message = f"{action.capitalize()} {request.flag_name} for user {request.user_id}"
        
        return {
            "success": True,
            "message": message,
            "flag_name": request.flag_name,
            "user_id": request.user_id,
            "enabled": request.enabled,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to add user override: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add user override: {str(e)}")


# Monitoring Endpoints
@router.get("/monitoring/dashboard")
async def get_monitoring_dashboard():
    """Get monitoring dashboard data."""
    try:
        monitor = get_monitor()
        dashboard_data = monitor.get_dashboard_data()
        return dashboard_data
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.get("/monitoring/dashboard/html", response_class=HTMLResponse)
async def get_monitoring_dashboard_html():
    """Get HTML monitoring dashboard."""
    try:
        monitor = get_monitor()
        html_content = create_monitoring_dashboard_html(monitor)
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Failed to generate HTML dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard: {str(e)}")


@router.get("/monitoring/alerts")
async def get_active_alerts():
    """Get active alerts."""
    try:
        monitor = get_monitor()
        dashboard_data = monitor.get_dashboard_data()
        return dashboard_data.get("alerts", {})
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.post("/monitoring/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an active alert."""
    try:
        monitor = get_monitor()
        success = monitor.acknowledge_alert(alert_id)
        
        if success:
            return {
                "success": True,
                "message": f"Alert {alert_id} acknowledged",
                "alert_id": alert_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.get("/monitoring/comparison")
async def get_performance_comparison(hours: int = Query(24, ge=1, le=168, description="Hours to compare (1-168)")):
    """Get performance comparison between clients."""
    try:
        monitor = get_monitor()
        comparison = monitor.get_performance_comparison(hours)
        return {
            "comparison": comparison,
            "time_period_hours": hours,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get performance comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get comparison: {str(e)}")


# Decision Endpoint
@router.get("/decision")
async def get_trends_client_decision(
    user_id: Optional[str] = Query(None, description="User ID for personalized routing"),
    keyword: Optional[str] = Query(None, description="Keyword for consistent routing")
):
    """Get which trends client should be used for a request."""
    try:
        flag_manager = get_flag_manager()
        use_simple_trends = flag_manager.should_use_simple_trends(user_id, keyword)
        
        client_type = TrendsClientType.SIMPLE_TRENDS if use_simple_trends else TrendsClientType.GOOGLE_TRENDS
        
        return {
            "client_type": client_type.value,
            "use_simple_trends": use_simple_trends,
            "user_id": user_id,
            "keyword": keyword,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get client decision: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get decision: {str(e)}")


# Health Check
@router.get("/health")
async def feature_flags_health_check():
    """Health check for feature flag system."""
    try:
        flag_manager = get_flag_manager()
        monitor = get_monitor()
        
        # Basic health checks
        flag_status = flag_manager.get_flag_status()
        dashboard_data = monitor.get_dashboard_data()
        
        health_status = {
            "status": "healthy",
            "feature_flags_operational": True,
            "monitoring_active": dashboard_data.get("monitoring_status", {}).get("active", False),
            "active_alerts": dashboard_data.get("alerts", {}).get("active_count", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        # Check if there are critical alerts
        alerts = dashboard_data.get("alerts", {}).get("active_alerts", [])
        critical_alerts = [alert for alert in alerts if alert.get("threshold", {}).get("severity") == "critical"]
        
        if critical_alerts:
            health_status["status"] = "degraded"
            health_status["critical_alerts"] = len(critical_alerts)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Feature flags health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Statistics Endpoint
@router.get("/statistics")
async def get_feature_flag_statistics():
    """Get comprehensive feature flag statistics."""
    try:
        flag_manager = get_flag_manager()
        monitor = get_monitor()
        
        # Get basic statistics
        flag_status = flag_manager.get_flag_status()
        performance_report = flag_manager.get_performance_report()
        dashboard_data = monitor.get_dashboard_data()
        
        statistics = {
            "feature_flags": flag_status,
            "performance_metrics": performance_report.get("performance_metrics", {}),
            "system_health": dashboard_data.get("system_health", {}),
            "monitoring_status": dashboard_data.get("monitoring_status", {}),
            "alerts_summary": {
                "active_alerts": dashboard_data.get("alerts", {}).get("active_count", 0),
                "recent_alerts": len(dashboard_data.get("alerts", {}).get("recent_alerts", [])),
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return statistics
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# Migration Control Endpoints
@router.post("/migration/start")
async def start_migration(target_percentage: float = Body(..., ge=0.0, le=100.0, embed=True)):
    """Start gradual migration to Simple Trends."""
    try:
        flag_manager = get_flag_manager()
        
        # Start with 0% and gradually increase
        flag_manager.update_flag_percentage(0.0)
        
        # This would typically trigger a gradual rollout process
        # For now, we'll just set the target percentage
        flag_manager.update_flag_percentage(target_percentage)
        
        return {
            "success": True,
            "message": f"Started migration to Simple Trends with {target_percentage}% target",
            "target_percentage": target_percentage,
            "current_percentage": target_percentage,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to start migration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start migration: {str(e)}")


@router.post("/migration/rollback")
async def rollback_migration():
    """Rollback migration to Google Trends."""
    try:
        flag_manager = get_flag_manager()
        
        # Disable all Simple Trends flags
        flag_manager.update_flag_percentage(0.0)
        flag_manager.disable_a_b_testing()
        flag_manager.disable_force_simple_trends()
        
        return {
            "success": True,
            "message": "Rolled back migration to Google Trends",
            "simple_trends_percentage": 0.0,
            "ab_testing_enabled": False,
            "force_flag_enabled": False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to rollback migration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rollback migration: {str(e)}")


@router.post("/migration/complete")
async def complete_migration():
    """Complete migration to Simple Trends (100%)."""
    try:
        flag_manager = get_flag_manager()
        
        # Set to 100% Simple Trends
        flag_manager.update_flag_percentage(100.0)
        flag_manager.disable_a_b_testing()  # No longer needed
        
        return {
            "success": True,
            "message": "Completed migration to Simple Trends (100%)",
            "simple_trends_percentage": 100.0,
            "ab_testing_enabled": False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to complete migration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete migration: {str(e)}")