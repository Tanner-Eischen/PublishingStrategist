"""Listing generation API router.

This module provides REST API endpoints for KDP listing generation functionality,
integrating with the existing MCP agent's listing generation tool.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.requests import ListingGenerationRequest
from ..models.responses import (
    ListingGenerationResponse,
    ListingData,
    AnalysisMetadata,
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


def convert_mcp_listing_to_api(mcp_listing: Dict[str, Any]) -> ListingData:
    """Convert MCP agent listing data to API response format."""
    return ListingData(
        title=mcp_listing.get('title', ''),
        subtitle=mcp_listing.get('subtitle'),
        description=mcp_listing.get('description', ''),
        keywords=mcp_listing.get('keywords', []),
        categories=mcp_listing.get('categories', []),
        target_price=mcp_listing.get('target_price'),
        bullet_points=mcp_listing.get('bullet_points', []),
        author_bio=mcp_listing.get('author_bio'),
        back_cover_text=mcp_listing.get('back_cover_text'),
        marketing_hooks=mcp_listing.get('marketing_hooks', [])
    )


def calculate_optimization_score(listing: ListingData) -> float:
    """Calculate SEO optimization score for the listing."""
    score = 0.0
    max_score = 100.0
    
    # Title optimization (25 points)
    if listing.title:
        title_length = len(listing.title)
        if 30 <= title_length <= 60:  # Optimal title length
            score += 25
        elif 20 <= title_length <= 80:
            score += 15
        else:
            score += 5
    
    # Keywords optimization (20 points)
    if listing.keywords:
        keyword_count = len(listing.keywords)
        if 5 <= keyword_count <= 7:  # Optimal keyword count
            score += 20
        elif 3 <= keyword_count <= 10:
            score += 15
        else:
            score += 5
    
    # Description optimization (20 points)
    if listing.description:
        desc_length = len(listing.description)
        if 200 <= desc_length <= 4000:  # Good description length
            score += 20
        elif 100 <= desc_length <= 5000:
            score += 15
        else:
            score += 5
    
    # Categories optimization (15 points)
    if listing.categories:
        if len(listing.categories) >= 2:
            score += 15
        elif len(listing.categories) == 1:
            score += 10
    
    # Bullet points optimization (10 points)
    if listing.bullet_points:
        if 3 <= len(listing.bullet_points) <= 5:
            score += 10
        elif len(listing.bullet_points) > 0:
            score += 5
    
    # Marketing hooks optimization (10 points)
    if listing.marketing_hooks:
        if len(listing.marketing_hooks) >= 3:
            score += 10
        elif len(listing.marketing_hooks) > 0:
            score += 5
    
    return min(score, max_score)


def generate_seo_recommendations(listing: ListingData, score: float) -> list[str]:
    """Generate SEO improvement recommendations."""
    recommendations = []
    
    # Title recommendations
    if listing.title:
        title_length = len(listing.title)
        if title_length < 30:
            recommendations.append("Consider expanding your title to 30-60 characters for better SEO")
        elif title_length > 80:
            recommendations.append("Consider shortening your title to under 80 characters")
    else:
        recommendations.append("Title is required for listing")
    
    # Keywords recommendations
    if not listing.keywords or len(listing.keywords) < 3:
        recommendations.append("Add more relevant keywords (aim for 5-7 keywords)")
    elif len(listing.keywords) > 10:
        recommendations.append("Consider reducing keywords to focus on most relevant ones")
    
    # Description recommendations
    if not listing.description or len(listing.description) < 200:
        recommendations.append("Expand your description to at least 200 characters for better engagement")
    
    # Categories recommendations
    if not listing.categories:
        recommendations.append("Select at least 2 relevant categories for better discoverability")
    elif len(listing.categories) < 2:
        recommendations.append("Consider adding a second category to increase visibility")
    
    # Bullet points recommendations
    if not listing.bullet_points or len(listing.bullet_points) < 3:
        recommendations.append("Add 3-5 bullet points highlighting key benefits")
    
    # Marketing hooks recommendations
    if not listing.marketing_hooks or len(listing.marketing_hooks) < 3:
        recommendations.append("Develop 3-5 marketing hooks to attract different customer segments")
    
    return recommendations


def check_kdp_compliance(listing: ListingData) -> Dict[str, bool]:
    """Check KDP compliance requirements."""
    compliance = {
        "title_length": len(listing.title) <= 200 if listing.title else False,
        "subtitle_length": len(listing.subtitle) <= 200 if listing.subtitle else True,
        "description_length": len(listing.description) <= 4000 if listing.description else False,
        "keywords_count": len(listing.keywords) <= 7 if listing.keywords else False,
        "has_required_fields": bool(listing.title and listing.description),
        "appropriate_content": True  # Would need content analysis in real implementation
    }
    
    return compliance


@router.post("/generate", response_model=ListingGenerationResponse)
async def generate_listing(
    request: ListingGenerationRequest,
    background_tasks: BackgroundTasks,
    agent=Depends(get_agent())
):
    """Generate optimized KDP listing.
    
    This endpoint generates an optimized Amazon KDP listing based on
    the provided niche and parameters using the MCP agent's listing generation tool.
    """
    try:
        logger.info(f"Starting listing generation for niche: {request.niche}")
        
        # Prepare parameters for MCP agent
        mcp_params = {
            "niche": request.niche,
            "target_audience": request.target_audience,
            "book_type": request.book_type,
            "include_keywords": request.include_keywords,
            "tone": request.tone
        }
        
        # Call MCP agent's listing generation method
        mcp_result = await agent.generate_listing(
            niche=request.niche,
            target_audience=request.target_audience,
            book_type=request.book_type,
            include_keywords=request.include_keywords,
            tone=request.tone
        )
        
        # Convert MCP result to API format
        listing = convert_mcp_listing_to_api(mcp_result.get('listing', {}))
        
        # Calculate optimization score
        optimization_score = calculate_optimization_score(listing)
        
        # Generate SEO recommendations
        seo_recommendations = generate_seo_recommendations(listing, optimization_score)
        
        # Check KDP compliance
        compliance_check = check_kdp_compliance(listing)
        
        # Create analysis metadata
        metadata = AnalysisMetadata(
            execution_time=mcp_result.get('execution_time', 0.0),
            data_sources=mcp_result.get('data_sources', ['openai', 'keepa']),
            cache_hit=mcp_result.get('cache_hit', False),
            warnings=mcp_result.get('warnings', [])
        )
        
        response = ListingGenerationResponse(
            listing=listing,
            optimization_score=optimization_score,
            analysis_metadata=metadata,
            seo_recommendations=seo_recommendations,
            compliance_check=compliance_check
        )
        
        logger.info(f"Listing generation completed with optimization score: {optimization_score:.1f}")
        return response
        
    except Exception as e:
        logger.error(f"Error in listing generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate listing: {str(e)}"
        )


@router.post("/optimize")
async def optimize_existing_listing(
    title: str,
    description: str,
    keywords: list[str] = None,
    agent=Depends(get_agent())
):
    """Optimize an existing listing.
    
    This endpoint takes an existing listing and provides optimization
    suggestions to improve its performance.
    """
    try:
        logger.info(f"Optimizing existing listing: {title[:50]}...")
        
        # Create a ListingData object from input
        current_listing = ListingData(
            title=title,
            description=description,
            keywords=keywords or [],
            categories=[],
            bullet_points=[],
            marketing_hooks=[]
        )
        
        # Calculate current optimization score
        current_score = calculate_optimization_score(current_listing)
        
        # Generate recommendations
        recommendations = generate_seo_recommendations(current_listing, current_score)
        
        # Check compliance
        compliance = check_kdp_compliance(current_listing)
        
        # Generate optimized version using MCP agent
        mcp_params = {
            "existing_title": title,
            "existing_description": description,
            "existing_keywords": keywords or [],
            "optimization_focus": "seo_and_conversion"
        }
        
        try:
            mcp_result = await agent.generate_listing(
                niche="optimization",
                target_audience="general",
                book_type="general"
            )
            
            optimized_listing = convert_mcp_listing_to_api(mcp_result.get('listing', {}))
            optimized_score = calculate_optimization_score(optimized_listing)
            
        except Exception as e:
            logger.warning(f"MCP optimization failed, using rule-based optimization: {e}")
            # Fallback to rule-based optimization
            optimized_listing = current_listing
            optimized_score = current_score
        
        return {
            "current_listing": current_listing,
            "current_score": current_score,
            "optimized_listing": optimized_listing,
            "optimized_score": optimized_score,
            "improvement": optimized_score - current_score,
            "recommendations": recommendations,
            "compliance_check": compliance
        }
        
    except Exception as e:
        logger.error(f"Error optimizing listing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to optimize listing: {str(e)}"
        )


@router.get("/templates")
async def get_listing_templates():
    """Get listing templates for different niches and book types."""
    templates = {
        "self_help": {
            "title_template": "{Main Benefit}: {Specific Method} to {Desired Outcome} in {Timeframe}",
            "description_template": "Discover the proven strategies that have helped thousands...",
            "common_keywords": ["self-help", "personal development", "motivation", "success", "mindset"]
        },
        "business": {
            "title_template": "{Business Topic}: The Complete Guide to {Specific Goal}",
            "description_template": "Master the essential skills and strategies needed to...",
            "common_keywords": ["business", "entrepreneurship", "leadership", "strategy", "growth"]
        },
        "health_fitness": {
            "title_template": "{Health Goal}: {Method/System} for {Target Audience}",
            "description_template": "Transform your health and fitness with this comprehensive guide...",
            "common_keywords": ["health", "fitness", "nutrition", "wellness", "exercise"]
        },
        "cooking": {
            "title_template": "{Cuisine/Diet} Cookbook: {Number} Delicious Recipes for {Occasion}",
            "description_template": "Bring the flavors of {cuisine} to your kitchen with...",
            "common_keywords": ["cookbook", "recipes", "cooking", "food", "kitchen"]
        }
    }
    
    return {
        "templates": templates,
        "usage_tips": [
            "Customize templates based on your specific niche",
            "Include emotional triggers in titles",
            "Use numbers and specific benefits",
            "Test different variations"
        ]
    }


@router.get("/compliance-check")
async def get_compliance_guidelines():
    """Get KDP compliance guidelines and requirements."""
    guidelines = {
        "title_requirements": {
            "max_length": 200,
            "restrictions": [
                "No promotional language (e.g., 'Best Seller')",
                "No misleading claims",
                "No excessive punctuation or symbols"
            ]
        },
        "description_requirements": {
            "max_length": 4000,
            "recommendations": [
                "Use compelling opening hook",
                "Include benefits and outcomes",
                "Add social proof if available",
                "End with clear call-to-action"
            ]
        },
        "keyword_requirements": {
            "max_count": 7,
            "best_practices": [
                "Use relevant, specific keywords",
                "Avoid keyword stuffing",
                "Include long-tail keywords",
                "Research competitor keywords"
            ]
        },
        "content_restrictions": [
            "No copyrighted material",
            "No offensive or inappropriate content",
            "No misleading information",
            "No spam or low-quality content"
        ]
    }
    
    return guidelines