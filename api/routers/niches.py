"""Niche discovery API router.

This module provides REST API endpoints for niche discovery functionality,
integrating with the existing MCP agent's niche discovery tool.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.requests import NicheDiscoveryRequest
from ..models.responses import (
    NicheDiscoveryResponse, 
    NicheData, 
    AnalysisMetadata, 
    ChartData,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_agent():
    """Dependency to get the MCP agent from app state."""
    from fastapi import Request
    
    def _get_agent(request: Request):
        if not hasattr(request.app.state, 'agent'):
            raise HTTPException(
                status_code=503,
                detail="MCP agent not available"
            )
        return request.app.state.agent
    
    return _get_agent


def convert_mcp_niche_to_api(mcp_niche: Dict[str, Any]) -> NicheData:
    """Convert MCP agent niche data to API response format."""
    return NicheData(
        name=mcp_niche.get('name', ''),
        score=float(mcp_niche.get('profitability_score', 0)),
        competition_level=mcp_niche.get('competition_level', 'unknown'),
        search_volume=int(mcp_niche.get('search_volume', 0)),
        trend_direction=mcp_niche.get('trend_direction', 'stable'),
        keywords=mcp_niche.get('keywords', []),
        estimated_revenue=mcp_niche.get('estimated_revenue'),
        seasonality=mcp_niche.get('seasonality'),
        barriers_to_entry=mcp_niche.get('barriers_to_entry', [])
    )


def create_niche_charts(niches: list[NicheData]) -> list[ChartData]:
    """Create chart data for niche visualization."""
    charts = []
    
    # Profitability score chart
    charts.append(ChartData(
        type="bar",
        title="Niche Profitability Scores",
        data=[
            {"name": niche.name, "score": niche.score}
            for niche in niches
        ],
        labels=[niche.name for niche in niches],
        colors=["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
    ))
    
    # Competition level distribution
    competition_counts = {}
    for niche in niches:
        level = niche.competition_level
        competition_counts[level] = competition_counts.get(level, 0) + 1
    
    charts.append(ChartData(
        type="pie",
        title="Competition Level Distribution",
        data=[
            {"label": level, "value": count}
            for level, count in competition_counts.items()
        ],
        colors=["#10B981", "#F59E0B", "#EF4444"]
    ))
    
    # Search volume vs profitability scatter
    charts.append(ChartData(
        type="scatter",
        title="Search Volume vs Profitability",
        data=[
            {
                "x": niche.search_volume,
                "y": niche.score,
                "label": niche.name
            }
            for niche in niches
        ]
    ))
    
    return charts


@router.post("/discover", response_model=NicheDiscoveryResponse)
async def discover_niches(
    request: NicheDiscoveryRequest,
    background_tasks: BackgroundTasks,
    agent=Depends(get_agent())
):
    """Discover profitable niches based on keywords.
    
    This endpoint analyzes the provided keywords to identify profitable
    niches using the MCP agent's niche discovery tool.
    """
    try:
        logger.info(f"Starting niche discovery for keywords: {request.base_keywords}")
        
        # Prepare parameters for MCP agent
        mcp_params = {
            "base_keywords": request.base_keywords,
            "max_niches": request.max_niches
        }
        
        # Add filters if provided
        if request.filters:
            mcp_params.update(request.filters)
        
        # Call MCP agent's niche discovery method
        mcp_result = await agent.discover_niches(
            keywords=request.base_keywords,
            max_niches=request.max_niches,
            **(request.filters or {})
        )
        
        # Convert MCP result to API format
        niches = [
            convert_mcp_niche_to_api(niche)
            for niche in mcp_result.get('niches', [])
        ]
        
        # Create visualization charts
        charts = create_niche_charts(niches)
        
        # Generate recommendations
        recommendations = []
        if niches:
            top_niche = max(niches, key=lambda n: n.score)
            recommendations.append(
                f"Consider focusing on '{top_niche.name}' with the highest profitability score of {top_niche.score:.1f}"
            )
            
            low_competition = [n for n in niches if n.competition_level == 'low']
            if low_competition:
                recommendations.append(
                    f"Found {len(low_competition)} low-competition niches for easier market entry"
                )
        
        # Create analysis metadata
        metadata = AnalysisMetadata(
            execution_time=mcp_result.get('execution_time', 0.0),
            data_sources=mcp_result.get('data_sources', ['keepa', 'google_trends']),
            cache_hit=mcp_result.get('cache_hit', False),
            warnings=mcp_result.get('warnings', [])
        )
        
        response = NicheDiscoveryResponse(
            niches=niches,
            total_analyzed=len(niches),
            analysis_metadata=metadata,
            charts=charts,
            recommendations=recommendations
        )
        
        logger.info(f"Niche discovery completed. Found {len(niches)} niches")
        return response
        
    except Exception as e:
        logger.error(f"Error in niche discovery: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover niches: {str(e)}"
        )


@router.get("/trending", response_model=NicheDiscoveryResponse)
async def get_trending_niches(
    limit: int = 10,
    timeframe: str = "7d",
    agent=Depends(get_agent())
):
    """Get currently trending niches.
    
    This endpoint returns niches that are currently trending
    based on search volume and market activity.
    """
    try:
        logger.info(f"Getting trending niches with limit: {limit}, timeframe: {timeframe}")
        
        # For now, use a default set of trending keywords
        # In a real implementation, this would come from trend analysis
        trending_keywords = [
            "productivity", "mindfulness", "remote work", 
            "sustainable living", "digital detox"
        ]
        
        # Call the niche discovery with trending keywords
        mcp_params = {
            "base_keywords": trending_keywords[:limit//2],  # Use subset
            "max_niches": limit,
            "trending_only": True
        }
        
        mcp_result = await agent.discover_niches(
            keywords=trending_keywords[:limit//2],
            max_niches=limit
        )
        
        # Convert and format response
        niches = [
            convert_mcp_niche_to_api(niche)
            for niche in mcp_result.get('niches', [])
        ]
        
        # Filter for trending niches (rising trend direction)
        trending_niches = [
            niche for niche in niches 
            if niche.trend_direction == 'rising'
        ]
        
        charts = create_niche_charts(trending_niches)
        
        metadata = AnalysisMetadata(
            execution_time=mcp_result.get('execution_time', 0.0),
            data_sources=['google_trends', 'keepa'],
            cache_hit=mcp_result.get('cache_hit', False)
        )
        
        response = NicheDiscoveryResponse(
            niches=trending_niches,
            total_analyzed=len(trending_niches),
            analysis_metadata=metadata,
            charts=charts,
            recommendations=[
                "These niches show strong upward trends in the past week",
                "Consider quick market entry for trending opportunities"
            ]
        )
        
        logger.info(f"Found {len(trending_niches)} trending niches")
        return response
        
    except Exception as e:
        logger.error(f"Error getting trending niches: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trending niches: {str(e)}"
        )


@router.get("/categories")
async def get_niche_categories():
    """Get available niche categories for filtering."""
    categories = [
        "Health & Fitness",
        "Business & Money",
        "Self-Help",
        "Technology",
        "Arts & Crafts",
        "Cooking & Food",
        "Travel",
        "Education",
        "Parenting",
        "Relationships",
        "Spirituality",
        "Sports",
        "Hobbies",
        "Home & Garden",
        "Fashion & Beauty"
    ]
    
    return {
        "categories": categories,
        "total": len(categories)
    }