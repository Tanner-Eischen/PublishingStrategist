"""Dashboard API router.

This module provides REST API endpoints for dashboard functionality,
including statistics and recent activity data.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Response models
class DashboardStats(BaseModel):
    """Dashboard statistics model."""
    totalAnalyses: int
    successfulListings: int
    averageScore: float
    trendsValidated: int
    totalRevenue: float = 0.0
    activeProjects: int = 0

class ActivityItem(BaseModel):
    """Recent activity item model."""
    id: int
    type: str
    title: str
    timestamp: str
    status: str
    score: float = None

class DashboardActivity(BaseModel):
    """Dashboard activity response model."""
    recent_activities: List[ActivityItem]
    total_count: int

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics.
    
    Returns aggregated statistics for the dashboard including:
    - Total analyses performed
    - Successful listings generated
    - Average performance score
    - Trends validated
    """
    try:
        # For now, return mock data that matches the frontend expectations
        # In a real implementation, this would query your database
        stats = DashboardStats(
            totalAnalyses=47,
            successfulListings=23,
            averageScore=78.5,
            trendsValidated=12,
            totalRevenue=15420.50,
            activeProjects=8
        )
        
        logger.info("Dashboard stats retrieved successfully")
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard statistics: {str(e)}"
        )

@router.get("/activity", response_model=DashboardActivity)
async def get_dashboard_activity(limit: int = 10):
    """Get recent dashboard activity.
    
    Args:
        limit: Maximum number of activity items to return (default: 10)
        
    Returns recent activity items including:
    - Analysis results
    - Listing generations
    - Trend validations
    - Other user actions
    """
    try:
        # For now, return mock data that matches the frontend expectations
        # In a real implementation, this would query your database
        recent_activities = [
            ActivityItem(
                id=1,
                type="niche_discovery",
                title="Self-Help Niche Analysis",
                timestamp=(datetime.now() - timedelta(hours=2)).isoformat(),
                status="completed",
                score=85.2
            ),
            ActivityItem(
                id=2,
                type="competitor_analysis",
                title="Romance Novel Market Research",
                timestamp=(datetime.now() - timedelta(hours=4)).isoformat(),
                status="completed",
                score=92.1
            ),
            ActivityItem(
                id=3,
                type="listing_generation",
                title="Cookbook Listing Created",
                timestamp=(datetime.now() - timedelta(hours=6)).isoformat(),
                status="completed",
                score=78.9
            ),
            ActivityItem(
                id=4,
                type="trend_validation",
                title="Mindfulness Trend Analysis",
                timestamp=(datetime.now() - timedelta(hours=8)).isoformat(),
                status="completed",
                score=88.7
            ),
            ActivityItem(
                id=5,
                type="niche_discovery",
                title="Tech Tutorial Niche",
                timestamp=(datetime.now() - timedelta(days=1)).isoformat(),
                status="completed",
                score=76.3
            ),
            ActivityItem(
                id=6,
                type="competitor_analysis",
                title="Fantasy Genre Analysis",
                timestamp=(datetime.now() - timedelta(days=1, hours=2)).isoformat(),
                status="completed",
                score=81.5
            ),
            ActivityItem(
                id=7,
                type="listing_generation",
                title="Travel Guide Listing",
                timestamp=(datetime.now() - timedelta(days=1, hours=4)).isoformat(),
                status="completed",
                score=89.2
            ),
            ActivityItem(
                id=8,
                type="trend_validation",
                title="Fitness Trend Research",
                timestamp=(datetime.now() - timedelta(days=2)).isoformat(),
                status="completed",
                score=83.6
            )
        ]
        
        # Limit the results
        limited_activities = recent_activities[:limit]
        
        activity_response = DashboardActivity(
            recent_activities=limited_activities,
            total_count=len(recent_activities)
        )
        
        logger.info(f"Dashboard activity retrieved successfully ({len(limited_activities)} items)")
        return activity_response
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard activity: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard activity: {str(e)}"
        )

@router.get("/summary")
async def get_dashboard_summary():
    """Get a combined dashboard summary with both stats and recent activity.
    
    This endpoint provides a single call to get both statistics and activity data.
    """
    try:
        stats = await get_dashboard_stats()
        activity = await get_dashboard_activity(limit=5)
        
        summary = {
            "stats": stats.dict(),
            "recent_activity": activity.dict(),
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info("Dashboard summary retrieved successfully")
        return summary
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard summary: {str(e)}"
        )