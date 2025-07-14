"""Competitor analysis API router.

This module provides REST API endpoints for competitor analysis functionality,
integrating with the existing MCP agent's competitor analysis tool.
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.requests import CompetitorAnalysisRequest
from ..models.responses import (
    CompetitorAnalysisResponse,
    CompetitorData,
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


def convert_mcp_competitor_to_api(mcp_competitor: Dict[str, Any]) -> CompetitorData:
    """Convert MCP agent competitor data to API response format."""
    return CompetitorData(
        asin=mcp_competitor.get('asin', ''),
        title=mcp_competitor.get('title', ''),
        author=mcp_competitor.get('author'),
        price=mcp_competitor.get('price'),
        rank=mcp_competitor.get('rank'),
        rating=mcp_competitor.get('rating'),
        review_count=mcp_competitor.get('review_count'),
        publication_date=mcp_competitor.get('publication_date'),
        page_count=mcp_competitor.get('page_count'),
        categories=mcp_competitor.get('categories', []),
        keywords=mcp_competitor.get('keywords', []),
        strengths=mcp_competitor.get('strengths', []),
        weaknesses=mcp_competitor.get('weaknesses', []),
        market_share=mcp_competitor.get('market_share')
    )


def create_competitor_charts(competitors: List[CompetitorData], market_overview: Dict[str, Any]) -> List[ChartData]:
    """Create chart data for competitor visualization."""
    charts = []
    
    # Price distribution chart
    price_data = [
        {"asin": comp.asin, "title": comp.title[:30] + "...", "price": comp.price}
        for comp in competitors if comp.price is not None
    ]
    
    if price_data:
        charts.append(ChartData(
            type="bar",
            title="Competitor Price Comparison",
            data=price_data,
            labels=[item["title"] for item in price_data],
            colors=["#3B82F6"] * len(price_data)
        ))
    
    # Rating vs Review Count scatter plot
    rating_data = [
        {
            "x": comp.review_count or 0,
            "y": comp.rating or 0,
            "label": comp.title[:20] + "...",
            "asin": comp.asin
        }
        for comp in competitors 
        if comp.rating is not None and comp.review_count is not None
    ]
    
    if rating_data:
        charts.append(ChartData(
            type="scatter",
            title="Rating vs Review Count",
            data=rating_data
        ))
    
    # Market share pie chart
    market_share_data = [
        {"label": comp.title[:20] + "...", "value": comp.market_share or 0}
        for comp in competitors if comp.market_share is not None
    ]
    
    if market_share_data:
        charts.append(ChartData(
            type="pie",
            title="Market Share Distribution",
            data=market_share_data,
            colors=["#10B981", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6"]
        ))
    
    # Best seller rank comparison
    rank_data = [
        {"asin": comp.asin, "title": comp.title[:30] + "...", "rank": comp.rank}
        for comp in competitors if comp.rank is not None
    ]
    
    if rank_data:
        # Sort by rank (lower is better)
        rank_data.sort(key=lambda x: x["rank"])
        charts.append(ChartData(
            type="bar",
            title="Best Seller Rank Comparison (Lower is Better)",
            data=rank_data,
            labels=[item["title"] for item in rank_data],
            colors=["#10B981"] * len(rank_data)
        ))
    
    return charts


def generate_market_insights(competitors: List[CompetitorData], market_overview: Dict[str, Any]) -> List[str]:
    """Generate insights from competitor analysis."""
    insights = []
    
    if competitors:
        # Price insights
        prices = [c.price for c in competitors if c.price is not None]
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            insights.append(
                f"Average competitor price: ${avg_price:.2f} (range: ${min_price:.2f} - ${max_price:.2f})"
            )
        
        # Rating insights
        ratings = [c.rating for c in competitors if c.rating is not None]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            insights.append(f"Average competitor rating: {avg_rating:.1f}/5.0")
        
        # Review count insights
        review_counts = [c.review_count for c in competitors if c.review_count is not None]
        if review_counts:
            avg_reviews = sum(review_counts) / len(review_counts)
            insights.append(f"Average review count: {int(avg_reviews)} reviews")
        
        # Competition level insight
        high_rated = len([c for c in competitors if c.rating and c.rating >= 4.0])
        if high_rated > len(competitors) * 0.7:
            insights.append("High competition: Most competitors have strong ratings (4.0+)")
        elif high_rated < len(competitors) * 0.3:
            insights.append("Opportunity: Many competitors have lower ratings (<4.0)")
    
    return insights


def identify_opportunities(competitors: List[CompetitorData]) -> List[str]:
    """Identify market opportunities based on competitor analysis."""
    opportunities = []
    
    if competitors:
        # Low rating opportunities
        low_rated = [c for c in competitors if c.rating and c.rating < 3.5]
        if low_rated:
            opportunities.append(
                f"Quality opportunity: {len(low_rated)} competitors have ratings below 3.5"
            )
        
        # High price opportunities
        prices = [c.price for c in competitors if c.price is not None]
        if prices:
            avg_price = sum(prices) / len(prices)
            if avg_price > 15:
                opportunities.append(
                    f"Price opportunity: Average price is ${avg_price:.2f} - consider competitive pricing"
                )
        
        # Low review count opportunities
        review_counts = [c.review_count for c in competitors if c.review_count is not None]
        if review_counts:
            low_review_count = len([c for c in review_counts if c < 100])
            if low_review_count > len(review_counts) * 0.5:
                opportunities.append(
                    "Market entry opportunity: Many competitors have fewer than 100 reviews"
                )
        
        # Keyword gaps
        all_keywords = set()
        for comp in competitors:
            all_keywords.update(comp.keywords)
        
        if len(all_keywords) < 20:
            opportunities.append(
                "SEO opportunity: Limited keyword diversity among competitors"
            )
    
    return opportunities


@router.post("/analyze", response_model=CompetitorAnalysisResponse)
async def analyze_competitors(
    request: CompetitorAnalysisRequest,
    background_tasks: BackgroundTasks,
    agent=Depends(get_agent())
):
    """Analyze competitors based on ASINs.
    
    This endpoint analyzes the provided Amazon ASINs to gather
    competitive intelligence using the MCP agent's competitor analysis tool.
    """
    try:
        logger.info(f"Starting competitor analysis for ASINs: {request.asins}")
        
        # Prepare parameters for MCP agent
        mcp_params = {
            "asins": request.asins,
            "analysis_depth": request.analysis_depth,
            "include_trends": request.include_trends
        }
        
        # Call MCP agent's competitor analysis method
        mcp_result = await agent.analyze_competitors(
            niche=request.asins[0] if request.asins else "general",
            analysis_depth=request.analysis_depth,
            include_trends=request.include_trends
        )
        
        # Convert MCP result to API format
        competitors = [
            convert_mcp_competitor_to_api(comp)
            for comp in mcp_result.get('competitors', [])
        ]
        
        # Extract market overview
        market_overview = mcp_result.get('market_overview', {})
        
        # Create visualization charts
        charts = create_competitor_charts(competitors, market_overview)
        
        # Generate insights and opportunities
        insights = generate_market_insights(competitors, market_overview)
        opportunities = identify_opportunities(competitors)
        
        # Create analysis metadata
        metadata = AnalysisMetadata(
            execution_time=mcp_result.get('execution_time', 0.0),
            data_sources=mcp_result.get('data_sources', ['keepa']),
            cache_hit=mcp_result.get('cache_hit', False),
            warnings=mcp_result.get('warnings', [])
        )
        
        response = CompetitorAnalysisResponse(
            competitors=competitors,
            market_overview=market_overview,
            analysis_metadata=metadata,
            charts=charts,
            insights=insights,
            opportunities=opportunities
        )
        
        logger.info(f"Competitor analysis completed. Analyzed {len(competitors)} competitors")
        return response
        
    except Exception as e:
        logger.error(f"Error in competitor analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze competitors: {str(e)}"
        )


@router.get("/search")
async def search_competitors(
    keyword: str,
    limit: int = 10,
    category: str = None,
    agent=Depends(get_agent())
):
    """Search for competitors by keyword.
    
    This endpoint searches for competitor products based on keywords
    and returns their ASINs for further analysis.
    """
    try:
        logger.info(f"Searching competitors for keyword: {keyword}")
        
        # This would typically use Amazon API or web scraping
        # For now, return mock data structure
        mock_results = [
            {
                "asin": f"B{i:09d}",
                "title": f"Sample Book {i} about {keyword}",
                "author": f"Author {i}",
                "price": 9.99 + i,
                "rating": 4.0 + (i % 5) * 0.2,
                "review_count": 100 + i * 50
            }
            for i in range(1, min(limit + 1, 11))
        ]
        
        return {
            "keyword": keyword,
            "results": mock_results,
            "total_found": len(mock_results),
            "category": category,
            "note": "This is mock data. Real implementation would use Amazon API or web scraping."
        }
        
    except Exception as e:
        logger.error(f"Error searching competitors: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search competitors: {str(e)}"
        )


@router.get("/market-overview")
async def get_market_overview(
    category: str = None,
    timeframe: str = "30d"
):
    """Get market overview statistics.
    
    This endpoint provides general market statistics and trends
    for the specified category and timeframe.
    """
    try:
        # Mock market overview data
        overview = {
            "category": category or "All Categories",
            "timeframe": timeframe,
            "total_products": 15420,
            "average_price": 12.99,
            "average_rating": 4.1,
            "top_keywords": [
                "productivity", "mindfulness", "self-help", 
                "business", "health", "fitness"
            ],
            "market_trends": {
                "growth_rate": 8.5,
                "new_entries": 234,
                "price_trend": "stable",
                "demand_level": "high"
            },
            "competition_metrics": {
                "saturation_level": "medium",
                "barrier_to_entry": "low",
                "average_reviews_needed": 150
            }
        }
        
        return overview
        
    except Exception as e:
        logger.error(f"Error getting market overview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get market overview: {str(e)}"
        )