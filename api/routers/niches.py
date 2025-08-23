"""Niche discovery API router.

This module provides REST API endpoints for niche discovery functionality,
integrating with the existing MCP agent's niche discovery tool.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
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


def get_agent(request: Request):
    """Dependency to get the MCP agent from app state."""
    if not hasattr(request.app.state, 'agent'):
        raise HTTPException(
            status_code=503,
            detail="MCP agent not available"
        )
    return request.app.state.agent


def convert_mcp_niche_to_api(mcp_niche: Dict[str, Any]) -> NicheData:
    """Convert MCP agent niche data to API response format."""
    from src.kdp_strategist.models.niche_model import CompetitionLevel, ProfitabilityTier, RiskLevel
    
    # Handle trend direction
    trend_data = mcp_niche.get("trend_analysis_data") or {}
    if not isinstance(trend_data, dict):
        trend_direction = getattr(trend_data, "trend_direction", "stable")
    else:
        trend_direction = trend_data.get("trend_direction", "stable")

    # Calculate search volume from market size score
    market_size_score = float(mcp_niche.get("market_size_score", 0))
    search_volume = int(market_size_score * 100)

    # Handle enum conversions with fallbacks
    competition_level_str = mcp_niche.get("competition_level", "medium")
    if isinstance(competition_level_str, str):
        try:
            competition_level = CompetitionLevel(competition_level_str.lower())
        except ValueError:
            competition_level = CompetitionLevel.MEDIUM
    else:
        competition_level = competition_level_str

    profitability_tier_str = mcp_niche.get("profitability_tier", "medium")
    if isinstance(profitability_tier_str, str):
        try:
            profitability_tier = ProfitabilityTier(profitability_tier_str.lower())
        except ValueError:
            profitability_tier = ProfitabilityTier.MEDIUM
    else:
        profitability_tier = profitability_tier_str

    risk_level_str = mcp_niche.get("risk_level", "medium")
    if isinstance(risk_level_str, str):
        try:
            risk_level = RiskLevel(risk_level_str.lower())
        except ValueError:
            risk_level = RiskLevel.MEDIUM
    else:
        risk_level = risk_level_str

    return NicheData(
        name=mcp_niche.get("primary_keyword", mcp_niche.get("name", "")),
        score=float(mcp_niche.get("profitability_score_numeric", mcp_niche.get("profitability_score", 0))),
        competition_level=competition_level,
        profitability_tier=profitability_tier,
        risk_level=risk_level,
        search_volume=search_volume,
        trend_direction=trend_direction,
        keywords=mcp_niche.get("keywords", []),
        estimated_revenue=mcp_niche.get("estimated_revenue"),
        seasonality=mcp_niche.get("seasonal_factors"),
        barriers_to_entry=mcp_niche.get("barriers_to_entry", [])
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
        level = niche.competition_level.value if hasattr(niche.competition_level, 'value') else str(niche.competition_level)
        competition_counts[level] = competition_counts.get(level, 0) + 1
    
    charts.append(ChartData(
        type="pie",
        title="Competition Level Distribution",
        data=[
            {"label": level.title(), "value": count}
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


@router.post(
    "/discover", 
    response_model=NicheDiscoveryResponse,
    summary="Discover Profitable Niches",
    description="""
    Analyze keywords to identify profitable publishing niches using AI-powered market analysis.
    
    This endpoint combines multiple data sources including Google Trends and Amazon market data
    to provide comprehensive niche analysis with profitability scoring, competition assessment,
    and market opportunity identification.
    
    **Rate Limit**: 10 requests per hour per IP address
    
    **Processing Time**: 30-120 seconds depending on keyword count and market complexity
    
    **WebSocket Support**: Real-time progress updates available via WebSocket connection
    """,
    responses={
        200: {
            "description": "Successful niche discovery analysis",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "niches": [
                            {
                                "name": "productivity journal",
                                "score": 78.5,
                                "competition_level": "medium",
                                "profitability_tier": "high",
                                "risk_level": "low",
                                "search_volume": 12000,
                                "trend_direction": "rising",
                                "keywords": ["productivity", "journal", "planner"],
                                "estimated_revenue": 2500.0,
                                "barriers_to_entry": ["Content creation", "Design skills"]
                            }
                        ],
                        "total_analyzed": 1,
                        "recommendations": [
                            "Consider focusing on 'productivity journal' with the highest profitability score of 78.5"
                        ]
                    }
                }
            }
        },
        400: {"description": "Invalid input parameters"},
        429: {"description": "Rate limit exceeded"},
        504: {"description": "Request timeout"},
        500: {"description": "Internal server error"}
    }
)
async def discover_niches(
    request: NicheDiscoveryRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    agent=Depends(get_agent)
):
    """Discover profitable niches based on keywords.
    
    This endpoint analyzes the provided keywords to identify profitable
    niches using the MCP agent's niche discovery tool with comprehensive
    market analysis including trend validation, competition assessment,
    and profitability scoring.
    """
    try:
        logger.info(f"Starting niche discovery for keywords: {request.base_keywords}")
        
        # Generate analysis ID for WebSocket tracking
        import uuid
        analysis_id = f"niche_discovery_{uuid.uuid4().hex[:8]}"
        
        # Get WebSocket manager from app state
        from fastapi import Request
        from api.main import manager
        
        # Start WebSocket progress tracking if client_id provided in headers
        client_id = http_request.headers.get('X-Client-ID')
        if client_id and client_id in manager.active_connections:
            manager.start_analysis(analysis_id, client_id, 'niche_discovery', {
                'base_keywords': request.base_keywords,
                'max_niches': request.max_niches,
                'filters': request.filters
            })
            
            # Send initial progress update
            await manager.update_analysis_progress(analysis_id, 0, 0, 'in-progress')
        
        # Prepare parameters for MCP agent
        mcp_params = {
            "base_keywords": request.base_keywords,
            "max_niches": request.max_niches,
            "analysis_id": analysis_id  # Pass analysis ID for progress tracking
        }
        
        # Add filters if provided
        if request.filters:
            mcp_params.update(request.filters)
        
        # Progress callback for WebSocket updates
        async def progress_callback(step: int, total_steps: int, message: str = None):
            if client_id and client_id in manager.active_connections:
                progress = int((step / total_steps) * 100)
                await manager.update_analysis_progress(
                    analysis_id, progress, step, 'in-progress', message
                )
        
        # Create progress tracker for WebSocket integration
        progress_tracker = None
        if client_id and client_id in manager.active_connections:
            from src.kdp_strategist.progress_tracker import ProgressTracker
            progress_tracker = ProgressTracker(analysis_id, manager)
        
        # Call MCP agent's niche discovery method with progress tracking
        try:
            mcp_result = await agent.find_profitable_niches(
                base_keywords=request.base_keywords,
                max_niches=request.max_niches,
                **(request.filters or {})
            )
        except AttributeError:
            # Fallback if method name is different
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
            
            from src.kdp_strategist.models.niche_model import CompetitionLevel
            low_competition = [n for n in niches if n.competition_level == CompetitionLevel.LOW]
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
        
        # Send completion notification via WebSocket
        if client_id and client_id in manager.active_connections:
            await manager.complete_analysis(analysis_id, response.dict())
        
        logger.info(f"Niche discovery completed. Found {len(niches)} niches")
        return response
        
    except ValueError as e:
        logger.error(f"Invalid input for niche discovery: {str(e)}")
        # Send error notification via WebSocket
        if 'client_id' in locals() and client_id and client_id in manager.active_connections:
            await manager.error_analysis(analysis_id, f"Invalid input parameters: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input parameters: {str(e)}"
        )
    except TimeoutError as e:
        logger.error(f"Timeout in niche discovery: {str(e)}")
        # Send error notification via WebSocket
        if 'client_id' in locals() and client_id and client_id in manager.active_connections:
            await manager.error_analysis(analysis_id, "Request timeout - please try again with fewer keywords")
        raise HTTPException(
            status_code=504,
            detail="Request timeout - please try again with fewer keywords or reduce max_niches"
        )
    except Exception as e:
        logger.error(f"Unexpected error in niche discovery: {str(e)}")
        # Send error notification via WebSocket
        if 'client_id' in locals() and client_id and client_id in manager.active_connections:
            await manager.error_analysis(analysis_id, f"Internal server error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error - please try again later"
        )


@router.get("/trending", response_model=NicheDiscoveryResponse)
async def get_trending_niches(
    limit: int = 10,
    timeframe: str = "7d",
    agent=Depends(get_agent)
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
        try:
            mcp_result = await agent.find_profitable_niches(
                base_keywords=trending_keywords[:limit//2],
                max_niches=limit
            )
        except AttributeError:
            # Fallback if method name is different
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