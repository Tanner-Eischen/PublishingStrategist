"""
Settings and user preferences API endpoints.
Handles user preferences, WebSocket settings, and application configuration.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Pydantic models for settings
class AnalysisPreferences(BaseModel):
    auto_save_results: bool = True
    show_progress_notifications: bool = True
    default_max_results: int = Field(20, ge=1, le=100)
    enable_real_time_updates: bool = True
    auto_export_completed: bool = False
    preferred_export_format: str = Field("csv", pattern="^(csv|json|xlsx)$")

class UIPreferences(BaseModel):
    theme: str = Field("light", pattern="^(light|dark|auto)$")
    results_per_page: int = Field(20, ge=10, le=100)
    show_advanced_options: bool = False
    compact_view: bool = False
    enable_animations: bool = True
    sidebar_collapsed: bool = False

class NotificationPreferences(BaseModel):
    browser_notifications: bool = True
    analysis_complete: bool = True
    error_alerts: bool = True
    progress_updates: bool = False
    sound_enabled: bool = False
    email_alerts: bool = False

class ProgressPreferences(BaseModel):
    show_floating_indicator: bool = True
    show_dashboard: bool = True
    auto_minimize_completed: bool = True
    show_detailed_steps: bool = True
    enable_progress_sounds: bool = False
    progress_update_interval: int = Field(1000, ge=500, le=10000)  # milliseconds
    show_time_estimates: bool = True
    show_cancellation_controls: bool = True

class WebSocketPreferences(BaseModel):
    auto_reconnect: bool = True
    reconnect_attempts: int = Field(5, ge=1, le=20)
    reconnect_delay: int = Field(3000, ge=1000, le=30000)  # milliseconds
    heartbeat_interval: int = Field(30000, ge=10000, le=300000)  # milliseconds
    connection_timeout: int = Field(10000, ge=5000, le=60000)  # milliseconds
    enable_compression: bool = False

class PerformancePreferences(BaseModel):
    enable_caching: bool = True
    cache_duration: int = Field(3600, ge=300, le=86400)  # seconds
    max_concurrent_analyses: int = Field(3, ge=1, le=10)
    enable_background_processing: bool = True
    auto_retry_failed: bool = True
    retry_attempts: int = Field(3, ge=1, le=10)

class PrivacyPreferences(BaseModel):
    save_search_history: bool = True
    share_usage_analytics: bool = False
    remember_api_settings: bool = True
    auto_clear_sensitive_data: bool = False

class UserPreferences(BaseModel):
    analysis: AnalysisPreferences = AnalysisPreferences()
    ui: UIPreferences = UIPreferences()
    notifications: NotificationPreferences = NotificationPreferences()
    progress: ProgressPreferences = ProgressPreferences()
    websocket: WebSocketPreferences = WebSocketPreferences()
    performance: PerformancePreferences = PerformancePreferences()
    privacy: PrivacyPreferences = PrivacyPreferences()
    
    last_updated: Optional[datetime] = None
    version: str = "1.0"

class PreferencesUpdateRequest(BaseModel):
    category: str = Field(..., pattern="^(analysis|ui|notifications|progress|websocket|performance|privacy)$")
    preferences: Dict[str, Any]

class BulkPreferencesUpdateRequest(BaseModel):
    preferences: Dict[str, Dict[str, Any]]

# In-memory storage for user preferences (in production, use database)
user_preferences_store: Dict[str, UserPreferences] = {}

def get_client_id(request: Request) -> str:
    """Extract client ID from request headers or generate a default one."""
    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        # Use session-based client ID or IP as fallback
        client_id = request.headers.get("X-Forwarded-For", request.client.host)
    return client_id or "default"

@router.get("/preferences", response_model=UserPreferences)
async def get_user_preferences(request: Request):
    """Get user preferences for the current client."""
    client_id = get_client_id(request)
    
    if client_id not in user_preferences_store:
        # Return default preferences
        user_preferences_store[client_id] = UserPreferences()
    
    return user_preferences_store[client_id]

@router.put("/preferences", response_model=UserPreferences)
async def update_user_preferences(
    preferences: UserPreferences,
    request: Request
):
    """Update all user preferences for the current client."""
    client_id = get_client_id(request)
    
    preferences.last_updated = datetime.utcnow()
    user_preferences_store[client_id] = preferences
    
    logger.info(f"Updated preferences for client {client_id}")
    return preferences

@router.patch("/preferences/{category}")
async def update_preference_category(
    category: str,
    update_request: Dict[str, Any],
    request: Request
):
    """Update a specific category of preferences."""
    client_id = get_client_id(request)
    
    # Validate category
    valid_categories = ["analysis", "ui", "notifications", "progress", "websocket", "performance", "privacy"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
    
    # Get current preferences or create default
    if client_id not in user_preferences_store:
        user_preferences_store[client_id] = UserPreferences()
    
    current_prefs = user_preferences_store[client_id]
    
    # Update the specific category
    try:
        category_data = getattr(current_prefs, category)
        category_dict = category_data.dict()
        category_dict.update(update_request)
        
        # Validate updated data
        category_models = {
            "analysis": AnalysisPreferences,
            "ui": UIPreferences,
            "notifications": NotificationPreferences,
            "progress": ProgressPreferences,
            "websocket": WebSocketPreferences,
            "performance": PerformancePreferences,
            "privacy": PrivacyPreferences
        }
        
        updated_category = category_models[category](**category_dict)
        setattr(current_prefs, category, updated_category)
        current_prefs.last_updated = datetime.utcnow()
        
        logger.info(f"Updated {category} preferences for client {client_id}")
        return {"success": True, "category": category, "updated_preferences": updated_category.dict()}
        
    except Exception as e:
        logger.error(f"Error updating {category} preferences: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid preferences data: {str(e)}")

@router.patch("/preferences")
async def bulk_update_preferences(
    update_request: BulkPreferencesUpdateRequest,
    request: Request
):
    """Update multiple preference categories at once."""
    client_id = get_client_id(request)
    
    # Get current preferences or create default
    if client_id not in user_preferences_store:
        user_preferences_store[client_id] = UserPreferences()
    
    current_prefs = user_preferences_store[client_id]
    updated_categories = []
    
    category_models = {
        "analysis": AnalysisPreferences,
        "ui": UIPreferences,
        "notifications": NotificationPreferences,
        "progress": ProgressPreferences,
        "websocket": WebSocketPreferences,
        "performance": PerformancePreferences,
        "privacy": PrivacyPreferences
    }
    
    try:
        for category, updates in update_request.preferences.items():
            if category not in category_models:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
            
            category_data = getattr(current_prefs, category)
            category_dict = category_data.dict()
            category_dict.update(updates)
            
            updated_category = category_models[category](**category_dict)
            setattr(current_prefs, category, updated_category)
            updated_categories.append(category)
        
        current_prefs.last_updated = datetime.utcnow()
        
        logger.info(f"Bulk updated preferences for client {client_id}: {updated_categories}")
        return {
            "success": True,
            "updated_categories": updated_categories,
            "preferences": current_prefs.dict()
        }
        
    except Exception as e:
        logger.error(f"Error bulk updating preferences: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid preferences data: {str(e)}")

@router.delete("/preferences")
async def reset_user_preferences(request: Request):
    """Reset user preferences to defaults."""
    client_id = get_client_id(request)
    
    user_preferences_store[client_id] = UserPreferences()
    
    logger.info(f"Reset preferences to defaults for client {client_id}")
    return {"success": True, "message": "Preferences reset to defaults"}

@router.delete("/preferences/{category}")
async def reset_preference_category(category: str, request: Request):
    """Reset a specific category of preferences to defaults."""
    client_id = get_client_id(request)
    
    # Validate category
    valid_categories = ["analysis", "ui", "notifications", "progress", "websocket", "performance", "privacy"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
    
    # Get current preferences or create default
    if client_id not in user_preferences_store:
        user_preferences_store[client_id] = UserPreferences()
    
    current_prefs = user_preferences_store[client_id]
    
    # Reset specific category to default
    category_models = {
        "analysis": AnalysisPreferences,
        "ui": UIPreferences,
        "notifications": NotificationPreferences,
        "progress": ProgressPreferences,
        "websocket": WebSocketPreferences,
        "performance": PerformancePreferences,
        "privacy": PrivacyPreferences
    }
    
    setattr(current_prefs, category, category_models[category]())
    current_prefs.last_updated = datetime.utcnow()
    
    logger.info(f"Reset {category} preferences to defaults for client {client_id}")
    return {
        "success": True,
        "category": category,
        "message": f"{category} preferences reset to defaults"
    }

@router.get("/preferences/export")
async def export_user_preferences(request: Request):
    """Export user preferences as JSON."""
    client_id = get_client_id(request)
    
    if client_id not in user_preferences_store:
        user_preferences_store[client_id] = UserPreferences()
    
    preferences = user_preferences_store[client_id]
    
    return {
        "client_id": client_id,
        "export_date": datetime.utcnow().isoformat(),
        "preferences": preferences.dict()
    }

@router.post("/preferences/import")
async def import_user_preferences(
    preferences_data: Dict[str, Any],
    request: Request
):
    """Import user preferences from JSON data."""
    client_id = get_client_id(request)
    
    try:
        # Extract preferences from import data
        if "preferences" in preferences_data:
            prefs_dict = preferences_data["preferences"]
        else:
            prefs_dict = preferences_data
        
        # Validate and create preferences object
        imported_prefs = UserPreferences(**prefs_dict)
        imported_prefs.last_updated = datetime.utcnow()
        
        user_preferences_store[client_id] = imported_prefs
        
        logger.info(f"Imported preferences for client {client_id}")
        return {
            "success": True,
            "message": "Preferences imported successfully",
            "preferences": imported_prefs.dict()
        }
        
    except Exception as e:
        logger.error(f"Error importing preferences: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid preferences data: {str(e)}")

@router.get("/websocket/status")
async def get_websocket_status(request: Request):
    """Get WebSocket connection status and statistics."""
    from api.main import manager
    
    client_id = get_client_id(request)
    
    # Get detailed analysis statistics
    analysis_stats = {
        'total': len(manager.active_analyses),
        'by_status': {},
        'by_type': {},
        'client_analyses': []
    }
    
    for analysis in manager.active_analyses.values():
        # Count by status
        status = analysis.get('status', 'unknown')
        analysis_stats['by_status'][status] = analysis_stats['by_status'].get(status, 0) + 1
        
        # Count by type
        analysis_type = analysis.get('type', 'unknown')
        analysis_stats['by_type'][analysis_type] = analysis_stats['by_type'].get(analysis_type, 0) + 1
        
        # Add client analyses
        if analysis.get('client_id') == client_id:
            analysis_stats['client_analyses'].append({
                'id': analysis['id'],
                'type': analysis['type'],
                'status': analysis['status'],
                'progress': analysis.get('progress', 0),
                'start_time': analysis.get('start_time'),
                'estimated_completion': analysis.get('estimated_completion')
            })
    
    return {
        "total_connections": len(manager.active_connections),
        "client_connected": client_id in manager.active_connections,
        "active_analyses": len(manager.active_analyses),
        "client_analyses": len(manager.client_analyses.get(client_id, set())),
        "analysis_statistics": analysis_stats,
        "server_time": datetime.utcnow().isoformat(),
        "uptime": datetime.utcnow().isoformat()  # Would be actual uptime in production
    }

@router.post("/analysis/cancel-all")
async def cancel_all_analyses(request: Request):
    """Cancel all active analyses for the current client."""
    from api.main import manager
    
    client_id = get_client_id(request)
    
    if client_id not in manager.client_analyses:
        return {"success": True, "message": "No active analyses to cancel", "cancelled_count": 0}
    
    cancelled_analyses = []
    for analysis_id in manager.client_analyses[client_id].copy():
        if manager.cancel_analysis(analysis_id, "Bulk cancellation by user"):
            cancelled_analyses.append(analysis_id)
    
    logger.info(f"Cancelled {len(cancelled_analyses)} analyses for client {client_id}")
    
    return {
        "success": True,
        "message": f"Cancelled {len(cancelled_analyses)} analyses",
        "cancelled_count": len(cancelled_analyses),
        "cancelled_analyses": cancelled_analyses
    }

@router.get("/analysis/history")
async def get_analysis_history(request: Request, limit: int = 50):
    """Get analysis history for the current client."""
    client_id = get_client_id(request)
    
    # In a real implementation, this would query a database
    # For now, return empty history as this is demo functionality
    return {
        "client_id": client_id,
        "history": [],
        "total_count": 0,
        "limit": limit,
        "message": "Analysis history feature coming soon"
    }

@router.delete("/analysis/history")
async def clear_analysis_history(request: Request):
    """Clear analysis history for the current client."""
    client_id = get_client_id(request)
    
    # In a real implementation, this would clear the database records
    logger.info(f"Analysis history cleared for client {client_id}")
    
    return {
        "success": True,
        "message": "Analysis history cleared",
        "client_id": client_id
    }

@router.get("/system/info")
async def get_system_info():
    """Get system information and capabilities."""
    return {
        "version": "1.0.0",
        "features": {
            "websocket_support": True,
            "real_time_progress": True,
            "analysis_cancellation": True,
            "analysis_pause_resume": True,
            "user_preferences": True,
            "export_import": True,
            "browser_notifications": True,
            "bulk_operations": True,
            "analysis_history": True,
            "session_management": True
        },
        "limits": {
            "max_concurrent_analyses": 10,
            "max_reconnect_attempts": 20,
            "max_results_per_page": 100,
            "max_cache_duration": 86400,
            "max_history_items": 1000
        },
        "supported_formats": ["csv", "json", "xlsx"],
        "supported_themes": ["light", "dark", "auto"],
        "websocket_endpoint": "/ws",
        "api_version": "v1"
    }