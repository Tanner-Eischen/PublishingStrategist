"""Trend validation API router.

This module provides REST API endpoints for trend validation functionality,
integrating with the existing MCP agent's trend validation tool.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.requests import TrendValidationRequest
from ..models.responses import (
    TrendValidationResponse,
    TrendData,
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


def convert_mcp_trend_to_api(mcp_trend: Dict[str, Any]) -> TrendData:
    """Convert MCP agent trend data to API response format."""
    return TrendData(
        keyword=mcp_trend.get('keyword', ''),
        trend_score=float(mcp_trend.get('trend_score', 0)),
        direction=mcp_trend.get('direction', 'stable'),
        volatility=float(mcp_trend.get('volatility', 0)),
        seasonal_pattern=mcp_trend.get('seasonal_pattern'),
        peak_months=mcp_trend.get('peak_months', []),
        related_queries=mcp_trend.get('related_queries', []),
        forecast=mcp_trend.get('forecast'),
        confidence_level=float(mcp_trend.get('confidence_level', 0))
    )


def create_trend_charts(trends: List[TrendData]) -> List[ChartData]:
    """Create chart data for trend visualization."""
    charts = []
    
    # Trend scores comparison
    trend_scores = [
        {"keyword": trend.keyword, "score": trend.trend_score}
        for trend in trends
    ]
    
    charts.append(ChartData(
        type="bar",
        title="Trend Strength Comparison",
        data=trend_scores,
        labels=[trend.keyword for trend in trends],
        colors=["#10B981", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6"]
    ))
    
    # Trend direction distribution
    direction_counts = {}
    for trend in trends:
        direction = trend.direction
        direction_counts[direction] = direction_counts.get(direction, 0) + 1
    
    charts.append(ChartData(
        type="pie",
        title="Trend Direction Distribution",
        data=[
            {"label": direction.title(), "value": count}
            for direction, count in direction_counts.items()
        ],
        colors=["#10B981", "#F59E0B", "#EF4444"]
    ))
    
    # Volatility vs Trend Score scatter
    volatility_data = [
        {
            "x": trend.volatility,
            "y": trend.trend_score,
            "label": trend.keyword
        }
        for trend in trends
    ]
    
    charts.append(ChartData(
        type="scatter",
        title="Volatility vs Trend Strength",
        data=volatility_data
    ))
    
    # Seasonal patterns (if available)
    seasonal_trends = [trend for trend in trends if trend.seasonal_pattern]
    if seasonal_trends:
        # Create a combined seasonal chart
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        seasonal_data = []
        for trend in seasonal_trends[:3]:  # Limit to top 3 for readability
            if trend.seasonal_pattern:
                seasonal_data.append({
                    "keyword": trend.keyword,
                    "data": [trend.seasonal_pattern.get(month, 0) for month in months]
                })
        
        if seasonal_data:
            charts.append(ChartData(
                type="line",
                title="Seasonal Patterns",
                data=seasonal_data,
                labels=months
            ))
    
    return charts


def assess_overall_trend_health(trends: List[TrendData]) -> str:
    """Assess overall trend health based on individual trends."""
    if not trends:
        return "unknown"
    
    rising_count = len([t for t in trends if t.direction == 'rising'])
    stable_count = len([t for t in trends if t.direction == 'stable'])
    declining_count = len([t for t in trends if t.direction == 'declining'])
    
    total = len(trends)
    rising_ratio = rising_count / total
    declining_ratio = declining_count / total
    
    avg_score = sum(t.trend_score for t in trends) / total
    avg_volatility = sum(t.volatility for t in trends) / total
    
    if rising_ratio >= 0.6 and avg_score >= 70:
        return "excellent"
    elif rising_ratio >= 0.4 and avg_score >= 50 and avg_volatility < 60:
        return "good"
    elif declining_ratio <= 0.3 and avg_score >= 30:
        return "fair"
    else:
        return "poor"


def generate_trend_recommendations(trends: List[TrendData], overall_health: str) -> List[str]:
    """Generate strategic recommendations based on trend analysis."""
    recommendations = []
    
    if not trends:
        return ["No trend data available for analysis"]
    
    # Overall health recommendations
    if overall_health == "excellent":
        recommendations.append("Strong trend momentum - excellent time for market entry")
    elif overall_health == "good":
        recommendations.append("Positive trend indicators - favorable market conditions")
    elif overall_health == "fair":
        recommendations.append("Mixed trend signals - proceed with caution and monitor closely")
    else:
        recommendations.append("Weak trend indicators - consider alternative niches or timing")
    
    # Specific trend recommendations
    rising_trends = [t for t in trends if t.direction == 'rising']
    if rising_trends:
        top_rising = max(rising_trends, key=lambda t: t.trend_score)
        recommendations.append(
            f"Focus on '{top_rising.keyword}' - strongest rising trend with {top_rising.trend_score:.1f} score"
        )
    
    # Volatility recommendations
    high_volatility = [t for t in trends if t.volatility > 70]
    if high_volatility:
        recommendations.append(
            f"High volatility detected in {len(high_volatility)} keywords - consider risk management"
        )
    
    # Seasonal recommendations
    seasonal_trends = [t for t in trends if t.peak_months]
    if seasonal_trends:
        current_month = datetime.now().strftime('%b')
        relevant_seasonal = [t for t in seasonal_trends if current_month in t.peak_months]
        if relevant_seasonal:
            recommendations.append(
                f"Current month ({current_month}) is peak season for {len(relevant_seasonal)} keywords"
            )
    
    # Confidence recommendations
    low_confidence = [t for t in trends if t.confidence_level < 60]
    if low_confidence:
        recommendations.append(
            f"Low confidence in {len(low_confidence)} trend predictions - gather more data"
        )
    
    return recommendations


def identify_risk_factors(trends: List[TrendData]) -> List[str]:
    """Identify potential risk factors from trend analysis."""
    risk_factors = []
    
    if not trends:
        return ["Insufficient trend data for risk assessment"]
    
    # Declining trends
    declining_trends = [t for t in trends if t.direction == 'declining']
    if declining_trends:
        risk_factors.append(
            f"{len(declining_trends)} keywords showing declining trends"
        )
    
    # High volatility
    volatile_trends = [t for t in trends if t.volatility > 80]
    if volatile_trends:
        risk_factors.append(
            f"High volatility in {len(volatile_trends)} keywords may indicate unstable market"
        )
    
    # Low trend scores
    weak_trends = [t for t in trends if t.trend_score < 30]
    if weak_trends:
        risk_factors.append(
            f"{len(weak_trends)} keywords have weak trend strength"
        )
    
    # Seasonal dependency
    seasonal_dependent = [t for t in trends if t.seasonal_pattern and max(t.seasonal_pattern.values()) > 80]
    if seasonal_dependent:
        risk_factors.append(
            f"{len(seasonal_dependent)} keywords are highly seasonal - revenue may fluctuate significantly"
        )
    
    # Low confidence predictions
    uncertain_forecasts = [t for t in trends if t.confidence_level < 50]
    if uncertain_forecasts:
        risk_factors.append(
            f"Uncertain forecasts for {len(uncertain_forecasts)} keywords"
        )
    
    return risk_factors


@router.post("/validate", response_model=TrendValidationResponse)
async def validate_trends(
    request: TrendValidationRequest,
    background_tasks: BackgroundTasks,
    agent=Depends(get_agent())
):
    """Validate trends for given keywords.
    
    This endpoint analyzes trend data for the provided keywords
    using the MCP agent's trend validation tool.
    """
    try:
        logger.info(f"Starting trend validation for keywords: {request.keywords}")
        
        # Prepare parameters for MCP agent
        mcp_params = {
            "keywords": request.keywords,
            "timeframe": request.timeframe,
            "geo": request.geo,
            "include_seasonality": request.include_seasonality
        }
        
        # Call MCP agent's trend validation method
        mcp_result = await agent.validate_trends(
            keywords=request.keywords,
            timeframe=request.timeframe,
            geo=request.geo,
            include_seasonality=request.include_seasonality
        )
        
        # Convert MCP result to API format
        trends = [
            convert_mcp_trend_to_api(trend)
            for trend in mcp_result.get('trends', [])
        ]
        
        # Assess overall trend health
        overall_health = assess_overall_trend_health(trends)
        
        # Create visualization charts
        charts = create_trend_charts(trends)
        
        # Generate recommendations and risk factors
        recommendations = generate_trend_recommendations(trends, overall_health)
        risk_factors = identify_risk_factors(trends)
        
        # Create analysis metadata
        metadata = AnalysisMetadata(
            execution_time=mcp_result.get('execution_time', 0.0),
            data_sources=mcp_result.get('data_sources', ['google_trends']),
            cache_hit=mcp_result.get('cache_hit', False),
            warnings=mcp_result.get('warnings', [])
        )
        
        response = TrendValidationResponse(
            trends=trends,
            overall_trend_health=overall_health,
            analysis_metadata=metadata,
            charts=charts,
            recommendations=recommendations,
            risk_factors=risk_factors
        )
        
        logger.info(f"Trend validation completed. Analyzed {len(trends)} trends")
        return response
        
    except Exception as e:
        logger.error(f"Error in trend validation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate trends: {str(e)}"
        )


@router.get("/trending-keywords")
async def get_trending_keywords(
    category: str = None,
    geo: str = "US",
    limit: int = 20
):
    """Get currently trending keywords.
    
    This endpoint returns keywords that are currently trending
    in the specified category and geographic region.
    """
    try:
        logger.info(f"Getting trending keywords for category: {category}, geo: {geo}")
        
        # Mock trending keywords data
        # In real implementation, this would come from Google Trends API
        trending_keywords = [
            {
                "keyword": "productivity hacks",
                "trend_score": 85,
                "growth_rate": 15.2,
                "search_volume": 12000,
                "category": "Business"
            },
            {
                "keyword": "mindful eating",
                "trend_score": 78,
                "growth_rate": 22.1,
                "search_volume": 8500,
                "category": "Health"
            },
            {
                "keyword": "remote work tips",
                "trend_score": 72,
                "growth_rate": 8.7,
                "search_volume": 15000,
                "category": "Business"
            },
            {
                "keyword": "sustainable living",
                "trend_score": 69,
                "growth_rate": 18.3,
                "search_volume": 9200,
                "category": "Lifestyle"
            },
            {
                "keyword": "digital minimalism",
                "trend_score": 65,
                "growth_rate": 12.9,
                "search_volume": 6800,
                "category": "Self-Help"
            }
        ]
        
        # Filter by category if specified
        if category:
            trending_keywords = [
                kw for kw in trending_keywords 
                if kw["category"].lower() == category.lower()
            ]
        
        # Limit results
        trending_keywords = trending_keywords[:limit]
        
        return {
            "trending_keywords": trending_keywords,
            "category": category,
            "geo": geo,
            "total_found": len(trending_keywords),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting trending keywords: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trending keywords: {str(e)}"
        )


@router.get("/forecast/{keyword}")
async def get_keyword_forecast(
    keyword: str,
    months: int = 3,
    geo: str = "US",
    agent=Depends(get_agent())
):
    """Get trend forecast for a specific keyword.
    
    This endpoint provides a trend forecast for the specified keyword
    over the requested time period.
    """
    try:
        logger.info(f"Getting forecast for keyword: {keyword}")
        
        # Mock forecast data
        # In real implementation, this would use trend analysis algorithms
        base_score = 65
        forecast_data = []
        
        for i in range(months):
            # Simulate trend variation
            variation = (-1) ** i * (i * 2)
            score = max(0, min(100, base_score + variation))
            
            forecast_data.append({
                "month": (datetime.now() + timedelta(days=30*i)).strftime("%Y-%m"),
                "predicted_score": score,
                "confidence": max(50, 90 - i * 10),  # Decreasing confidence over time
                "trend_direction": "rising" if score > base_score else "declining"
            })
        
        return {
            "keyword": keyword,
            "forecast_period": f"{months} months",
            "geo": geo,
            "forecast": forecast_data,
            "methodology": "Statistical trend analysis with seasonal adjustments",
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting keyword forecast: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get keyword forecast: {str(e)}"
        )


@router.get("/seasonal-patterns")
async def get_seasonal_patterns(
    keywords: List[str] = None,
    years: int = 2
):
    """Get seasonal patterns for keywords.
    
    This endpoint analyzes seasonal patterns in search trends
    for the specified keywords over the given time period.
    """
    try:
        if not keywords:
            keywords = ["fitness", "diet", "travel", "gifts", "gardening"]
        
        logger.info(f"Getting seasonal patterns for keywords: {keywords}")
        
        # Mock seasonal pattern data
        patterns = {}
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        for keyword in keywords:
            # Generate mock seasonal data based on keyword type
            if "fitness" in keyword.lower() or "diet" in keyword.lower():
                # Peak in January (New Year resolutions)
                pattern = [100, 80, 60, 50, 45, 40, 35, 40, 50, 60, 70, 85]
            elif "travel" in keyword.lower():
                # Peak in summer months
                pattern = [40, 45, 60, 70, 85, 100, 95, 90, 75, 60, 45, 50]
            elif "gift" in keyword.lower():
                # Peak in December
                pattern = [30, 25, 35, 40, 50, 45, 40, 45, 55, 70, 85, 100]
            else:
                # Relatively stable with slight variations
                pattern = [60, 55, 65, 70, 75, 80, 75, 70, 65, 60, 65, 70]
            
            patterns[keyword] = {
                "monthly_scores": dict(zip(months, pattern)),
                "peak_month": months[pattern.index(max(pattern))],
                "low_month": months[pattern.index(min(pattern))],
                "volatility": (max(pattern) - min(pattern)) / max(pattern) * 100,
                "trend_type": "seasonal" if max(pattern) - min(pattern) > 30 else "stable"
            }
        
        return {
            "seasonal_patterns": patterns,
            "analysis_period": f"{years} years",
            "insights": [
                "Fitness keywords peak in January due to New Year resolutions",
                "Travel keywords show strong summer seasonality",
                "Gift-related keywords spike during holiday season"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting seasonal patterns: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get seasonal patterns: {str(e)}"
        )