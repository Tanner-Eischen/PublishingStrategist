"""Competitor Analysis Tool.

Analyzes Amazon product competition using Keepa data to evaluate:
- Product performance metrics (BSR, sales estimates, reviews)
- Price analysis and trends
- Market positioning and gaps
- Competitive landscape assessment
- Revenue and profitability estimates

The tool provides detailed insights into:
- Individual product analysis (ASIN-based)
- Competitive benchmarking
- Market opportunity identification
- Strategic positioning recommendations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from statistics import mean, median

from ...data.cache_manager import CacheManager
from ...data.keepa_client import KeepaClient, ProductData
from ...models.niche_model import Niche

logger = logging.getLogger(__name__)


@dataclass
class CompetitorMetrics:
    """Metrics for a single competitor product."""
    asin: str
    title: str
    current_price: float
    bsr: Optional[int]
    category: str
    review_count: int
    rating: float
    estimated_monthly_sales: Optional[int]
    estimated_monthly_revenue: Optional[float]
    price_history: List[Tuple[datetime, float]]
    bsr_history: List[Tuple[datetime, int]]
    launch_date: Optional[datetime]
    
    # Calculated metrics
    price_stability: float = 0.0
    sales_trend: str = "stable"
    market_position: str = "unknown"
    competitive_strength: float = 0.0


@dataclass
class MarketAnalysis:
    """Overall market analysis for a niche or keyword."""
    keyword: str
    total_products: int
    avg_price: float
    price_range: Tuple[float, float]
    avg_reviews: float
    avg_rating: float
    market_saturation: str
    entry_barriers: str
    opportunity_score: float
    top_performers: List[CompetitorMetrics]
    market_gaps: List[Dict[str, Any]]
    recommendations: List[str]


class CompetitorAnalyzer:
    """Core analyzer for competitor data and market insights."""

    # BSR to sales estimation (rough approximations)
    BSR_LEVEL_1 = 1
    BSR_LEVEL_10 = 10
    BSR_LEVEL_100 = 100
    BSR_LEVEL_1000 = 1000
    BSR_LEVEL_10000 = 10000
    BSR_LEVEL_100000 = 100000
    BSR_LEVEL_1000000 = 1000000

    BSR_SALES_MAPPING = {
        BSR_LEVEL_1: 3000,
        BSR_LEVEL_10: 1500,
        BSR_LEVEL_100: 300,
        BSR_LEVEL_1000: 50,
        BSR_LEVEL_10000: 10,
        BSR_LEVEL_100000: 2,
        BSR_LEVEL_1000000: 0.5,
    }
    
    @classmethod
    def estimate_monthly_sales(cls, bsr: Optional[int], category: str = "Books") -> Optional[int]:
        """Estimate monthly sales based on BSR."""
        if not bsr or bsr <= 0:
            return None
        
        # Find closest BSR mapping
        for threshold, sales in sorted(cls.BSR_SALES_MAPPING.items()):
            if bsr <= threshold:
                return sales
        
        # For very high BSR (low sales)
        return max(
            1,
            int(
                cls.BSR_SALES_MAPPING[cls.BSR_LEVEL_1000000]
                * (cls.BSR_LEVEL_1000000 / bsr)
            ),
        )
    
    @classmethod
    def calculate_price_stability(cls, price_history: List[Tuple[datetime, float]]) -> float:
        """Calculate price stability score (0-100)."""
        if len(price_history) < 2:
            return 100.0
        
        prices = [price for _, price in price_history]
        if not prices:
            return 100.0
        
        # Calculate coefficient of variation
        avg_price = mean(prices)
        if avg_price == 0:
            return 0.0
        
        price_std = (sum((p - avg_price) ** 2 for p in prices) / len(prices)) ** 0.5
        cv = price_std / avg_price
        
        # Convert to stability score (lower CV = higher stability)
        stability = max(0, 100 - (cv * 100))
        return min(100, stability)
    
    @classmethod
    def analyze_sales_trend(cls, bsr_history: List[Tuple[datetime, int]]) -> str:
        """Analyze sales trend from BSR history."""
        if len(bsr_history) < 3:
            return "insufficient_data"
        
        # Sort by date
        sorted_history = sorted(bsr_history, key=lambda x: x[0])
        
        # Compare recent vs older BSR (lower BSR = better sales)
        recent_bsr = mean([bsr for _, bsr in sorted_history[-3:]])
        older_bsr = mean([bsr for _, bsr in sorted_history[:3]])
        
        if recent_bsr < older_bsr * 0.8:  # Significant improvement
            return "rising"
        elif recent_bsr > older_bsr * 1.2:  # Significant decline
            return "declining"
        else:
            return "stable"
    
    @classmethod
    def calculate_competitive_strength(cls, metrics: CompetitorMetrics) -> float:
        """Calculate overall competitive strength score (0-100)."""
        scores = []
        
        # Review count score (more reviews = stronger position)
        if metrics.review_count >= 1000:
            review_score = 90
        elif metrics.review_count >= 100:
            review_score = 70
        elif metrics.review_count >= 10:
            review_score = 50
        else:
            review_score = 20
        scores.append(review_score)
        
        # Rating score
        rating_score = (metrics.rating / 5.0) * 100 if metrics.rating else 50
        scores.append(rating_score)
        
        # Sales performance score (based on estimated sales)
        if metrics.estimated_monthly_sales:
            if metrics.estimated_monthly_sales >= 1000:
                sales_score = 95
            elif metrics.estimated_monthly_sales >= 100:
                sales_score = 80
            elif metrics.estimated_monthly_sales >= 10:
                sales_score = 60
            else:
                sales_score = 30
        else:
            sales_score = 40
        scores.append(sales_score)
        
        # Price stability score
        scores.append(metrics.price_stability)
        
        # Sales trend score
        trend_scores = {"rising": 90, "stable": 70, "declining": 30, "insufficient_data": 50}
        scores.append(trend_scores.get(metrics.sales_trend, 50))
        
        return mean(scores)
    
    @classmethod
    def identify_market_gaps(cls, competitors: List[CompetitorMetrics]) -> List[Dict[str, Any]]:
        """Identify potential market gaps and opportunities."""
        gaps = []
        
        if not competitors:
            return [{"type": "empty_market", "description": "No significant competition found", "opportunity": "high"}]
        
        # Price gap analysis
        prices = [c.current_price for c in competitors if c.current_price > 0]
        if prices:
            price_gaps = cls._find_price_gaps(prices)
            gaps.extend(price_gaps)
        
        # Quality gap analysis
        low_rated = [c for c in competitors if c.rating < 3.5]
        if len(low_rated) > len(competitors) * 0.3:  # 30% or more have low ratings
            gaps.append({
                "type": "quality_gap",
                "description": "Many competitors have poor ratings",
                "opportunity": "high",
                "avg_rating": mean([c.rating for c in low_rated])
            })
        
        # Review gap analysis
        low_review_count = [c for c in competitors if c.review_count < 50]
        if len(low_review_count) > len(competitors) * 0.5:  # 50% or more have few reviews
            gaps.append({
                "type": "review_gap",
                "description": "Many competitors have few reviews",
                "opportunity": "medium",
                "avg_reviews": mean([c.review_count for c in low_review_count])
            })
        
        # Content/positioning gaps (based on title analysis)
        title_keywords = cls._analyze_title_keywords([c.title for c in competitors])
        if len(title_keywords) < 10:  # Limited keyword diversity
            gaps.append({
                "type": "content_gap",
                "description": "Limited keyword diversity in titles",
                "opportunity": "medium",
                "common_keywords": list(title_keywords.keys())[:5]
            })
        
        return gaps
    
    @classmethod
    def _find_price_gaps(cls, prices: List[float]) -> List[Dict[str, Any]]:
        """Find gaps in price distribution."""
        gaps = []
        sorted_prices = sorted(prices)
        
        # Look for significant gaps between price points
        for i in range(len(sorted_prices) - 1):
            current = sorted_prices[i]
            next_price = sorted_prices[i + 1]
            gap_size = next_price - current
            
            # If gap is more than 50% of current price, it's significant
            if gap_size > current * 0.5 and gap_size > 2.0:
                gaps.append({
                    "type": "price_gap",
                    "description": f"Price gap between ${current:.2f} and ${next_price:.2f}",
                    "opportunity": "medium" if gap_size < current else "high",
                    "suggested_price": round(current + (gap_size / 2), 2)
                })
        
        return gaps
    
    @classmethod
    def _analyze_title_keywords(cls, titles: List[str]) -> Dict[str, int]:
        """Analyze keyword frequency in competitor titles."""
        keyword_counts = {}
        
        for title in titles:
            # Simple keyword extraction (split and clean)
            words = title.lower().split()
            for word in words:
                # Clean word (remove punctuation)
                clean_word = ''.join(c for c in word if c.isalnum())
                if len(clean_word) > 2:  # Ignore very short words
                    keyword_counts[clean_word] = keyword_counts.get(clean_word, 0) + 1
        
        # Return words that appear in multiple titles
        return {k: v for k, v in keyword_counts.items() if v > 1}


async def analyze_competitor_asin(
    keepa_client: KeepaClient,
    cache_manager: CacheManager,
    asin: str,
    include_history: bool = True,
    history_days: int = 90
) -> Dict[str, Any]:
    """Analyze a specific competitor product by ASIN.
    
    Args:
        keepa_client: Keepa API client
        cache_manager: Cache manager for performance
        asin: Amazon product ASIN to analyze
        include_history: Whether to include price/BSR history
        history_days: Number of days of history to analyze
    
    Returns:
        Dictionary containing detailed competitor analysis
    """
    logger.info(f"Analyzing competitor ASIN: {asin}")
    
    try:
        # Get product data from Keepa
        product_data = await keepa_client.get_product_data(asin)
        
        if not product_data:
            return {
                "error": "Product not found or data unavailable",
                "asin": asin,
                "analysis_timestamp": datetime.now().isoformat()
            }
        
        # Create competitor metrics
        metrics = CompetitorMetrics(
            asin=asin,
            title=product_data.title or "Unknown",
            current_price=product_data.current_price or 0.0,
            bsr=product_data.bsr,
            category=product_data.category or "Unknown",
            review_count=product_data.review_count or 0,
            rating=product_data.rating or 0.0,
            estimated_monthly_sales=CompetitorAnalyzer.estimate_monthly_sales(product_data.bsr),
            estimated_monthly_revenue=None,
            price_history=[],
            bsr_history=[],
            launch_date=product_data.launch_date
        )
        
        # Calculate estimated revenue
        if metrics.estimated_monthly_sales and metrics.current_price:
            metrics.estimated_monthly_revenue = metrics.estimated_monthly_sales * metrics.current_price
        
        # Get historical data if requested
        if include_history:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=history_days)
            
            # Get price history
            price_history = await keepa_client.get_price_history(asin, start_date, end_date)
            metrics.price_history = price_history or []
            
            # Get BSR history
            bsr_history = await keepa_client.get_bsr_history(asin, start_date, end_date)
            metrics.bsr_history = bsr_history or []
            
            # Calculate derived metrics
            metrics.price_stability = CompetitorAnalyzer.calculate_price_stability(metrics.price_history)
            metrics.sales_trend = CompetitorAnalyzer.analyze_sales_trend(metrics.bsr_history)
        
        # Calculate competitive strength
        metrics.competitive_strength = CompetitorAnalyzer.calculate_competitive_strength(metrics)
        
        # Determine market position
        if metrics.competitive_strength >= 80:
            metrics.market_position = "dominant"
        elif metrics.competitive_strength >= 60:
            metrics.market_position = "strong"
        elif metrics.competitive_strength >= 40:
            metrics.market_position = "moderate"
        else:
            metrics.market_position = "weak"
        
        # Generate insights and recommendations
        insights = _generate_competitor_insights(metrics)
        recommendations = _generate_competitive_recommendations(metrics)
        
        result = {
            "asin": asin,
            "basic_info": {
                "title": metrics.title,
                "category": metrics.category,
                "current_price": metrics.current_price,
                "launch_date": metrics.launch_date.isoformat() if metrics.launch_date else None
            },
            "performance_metrics": {
                "bsr": metrics.bsr,
                "review_count": metrics.review_count,
                "rating": metrics.rating,
                "estimated_monthly_sales": metrics.estimated_monthly_sales,
                "estimated_monthly_revenue": metrics.estimated_monthly_revenue
            },
            "competitive_analysis": {
                "competitive_strength": metrics.competitive_strength,
                "market_position": metrics.market_position,
                "price_stability": metrics.price_stability,
                "sales_trend": metrics.sales_trend
            },
            "historical_data": {
                "price_history_points": len(metrics.price_history),
                "bsr_history_points": len(metrics.bsr_history),
                "analysis_period_days": history_days if include_history else 0
            },
            "insights": insights,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Competitor analysis completed for ASIN: {asin}")
        return result
    
    except Exception as e:
        logger.error(f"Competitor analysis failed for ASIN {asin}: {e}")
        return {
            "error": str(e),
            "asin": asin,
            "analysis_timestamp": datetime.now().isoformat()
        }


async def analyze_market_competition(
    keepa_client: KeepaClient,
    cache_manager: CacheManager,
    keyword: str,
    category: Optional[str] = None,
    max_products: int = 20,
    min_reviews: int = 0
) -> Dict[str, Any]:
    """Analyze overall market competition for a keyword/niche.
    
    Args:
        keepa_client: Keepa API client
        cache_manager: Cache manager for performance
        keyword: Keyword to analyze competition for
        category: Amazon category to focus on
        max_products: Maximum number of products to analyze
        min_reviews: Minimum review count filter
    
    Returns:
        Dictionary containing market competition analysis
    """
    logger.info(f"Analyzing market competition for keyword: {keyword}")
    
    try:
        # Search for products
        products = await keepa_client.search_products(
            keyword, 
            category=category, 
            limit=max_products
        )
        
        if not products:
            return {
                "keyword": keyword,
                "total_products": 0,
                "message": "No products found for this keyword",
                "analysis_timestamp": datetime.now().isoformat()
            }
        
        # Filter products by minimum reviews
        filtered_products = [p for p in products if (p.review_count or 0) >= min_reviews]
        
        # Convert to competitor metrics
        competitors = []
        for product in filtered_products:
            metrics = CompetitorMetrics(
                asin=product.asin,
                title=product.title or "Unknown",
                current_price=product.current_price or 0.0,
                bsr=product.bsr,
                category=product.category or "Unknown",
                review_count=product.review_count or 0,
                rating=product.rating or 0.0,
                estimated_monthly_sales=CompetitorAnalyzer.estimate_monthly_sales(product.bsr),
                estimated_monthly_revenue=None,
                price_history=[],
                bsr_history=[],
                launch_date=product.launch_date
            )
            
            # Calculate estimated revenue
            if metrics.estimated_monthly_sales and metrics.current_price:
                metrics.estimated_monthly_revenue = metrics.estimated_monthly_sales * metrics.current_price
            
            # Calculate competitive strength (without historical data)
            metrics.competitive_strength = CompetitorAnalyzer.calculate_competitive_strength(metrics)
            
            competitors.append(metrics)
        
        # Analyze market
        market_analysis = _analyze_market_metrics(keyword, competitors)
        
        # Generate market insights
        market_insights = _generate_market_insights(market_analysis)
        
        result = {
            "keyword": keyword,
            "category": category,
            "total_products_found": len(products),
            "analyzed_products": len(competitors),
            "market_metrics": {
                "avg_price": market_analysis.avg_price,
                "price_range": {"min": market_analysis.price_range[0], "max": market_analysis.price_range[1]},
                "avg_reviews": market_analysis.avg_reviews,
                "avg_rating": market_analysis.avg_rating,
                "market_saturation": market_analysis.market_saturation,
                "entry_barriers": market_analysis.entry_barriers,
                "opportunity_score": market_analysis.opportunity_score
            },
            "top_performers": [
                {
                    "asin": comp.asin,
                    "title": comp.title[:100] + "..." if len(comp.title) > 100 else comp.title,
                    "price": comp.current_price,
                    "reviews": comp.review_count,
                    "rating": comp.rating,
                    "competitive_strength": comp.competitive_strength,
                    "estimated_monthly_sales": comp.estimated_monthly_sales
                }
                for comp in market_analysis.top_performers
            ],
            "market_gaps": market_analysis.market_gaps,
            "insights": market_insights,
            "recommendations": market_analysis.recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Market competition analysis completed for keyword: {keyword}")
        return result
    
    except Exception as e:
        logger.error(f"Market competition analysis failed for keyword {keyword}: {e}")
        return {
            "error": str(e),
            "keyword": keyword,
            "analysis_timestamp": datetime.now().isoformat()
        }


def _generate_competitor_insights(metrics: CompetitorMetrics) -> List[str]:
    """Generate insights about a specific competitor."""
    insights = []
    
    # Performance insights
    if metrics.estimated_monthly_sales:
        if metrics.estimated_monthly_sales >= 1000:
            insights.append(f"High-performing product with estimated {metrics.estimated_monthly_sales:,} monthly sales")
        elif metrics.estimated_monthly_sales >= 100:
            insights.append(f"Moderate performer with estimated {metrics.estimated_monthly_sales:,} monthly sales")
        else:
            insights.append(f"Low sales volume with estimated {metrics.estimated_monthly_sales:,} monthly sales")
    
    # Review insights
    if metrics.review_count >= 1000:
        insights.append("Well-established product with strong review base")
    elif metrics.review_count >= 100:
        insights.append("Moderately established with decent review count")
    elif metrics.review_count < 10:
        insights.append("New or low-visibility product with few reviews")
    
    # Rating insights
    if metrics.rating >= 4.5:
        insights.append("Excellent customer satisfaction with high ratings")
    elif metrics.rating >= 4.0:
        insights.append("Good customer satisfaction")
    elif metrics.rating < 3.5:
        insights.append("Poor customer satisfaction - potential opportunity")
    
    # Price insights
    if metrics.current_price >= 20:
        insights.append("Premium pricing strategy")
    elif metrics.current_price <= 5:
        insights.append("Budget/low-cost positioning")
    
    # Trend insights
    if metrics.sales_trend == "rising":
        insights.append("Sales momentum is increasing")
    elif metrics.sales_trend == "declining":
        insights.append("Sales appear to be declining")
    
    return insights


def _generate_competitive_recommendations(metrics: CompetitorMetrics) -> List[str]:
    """Generate competitive recommendations based on analysis."""
    recommendations = []
    
    # Competitive positioning
    if metrics.competitive_strength < 50:
        recommendations.append("Weak competitor - consider direct competition with better quality/marketing")
    elif metrics.competitive_strength > 80:
        recommendations.append("Strong competitor - avoid direct competition, find differentiation angle")
    
    # Pricing recommendations
    if metrics.current_price > 15:
        recommendations.append("Consider lower-priced alternative to capture price-sensitive customers")
    elif metrics.current_price < 8:
        recommendations.append("Opportunity for premium positioning with higher quality")
    
    # Quality recommendations
    if metrics.rating < 4.0:
        recommendations.append("Focus on quality improvements to outperform this competitor")
    
    # Market entry recommendations
    if metrics.review_count < 50:
        recommendations.append("Low review count suggests market entry opportunity")
    
    return recommendations


def _analyze_market_metrics(keyword: str, competitors: List[CompetitorMetrics]) -> MarketAnalysis:
    """Analyze overall market metrics."""
    if not competitors:
        return MarketAnalysis(
            keyword=keyword,
            total_products=0,
            avg_price=0,
            price_range=(0, 0),
            avg_reviews=0,
            avg_rating=0,
            market_saturation="unknown",
            entry_barriers="unknown",
            opportunity_score=50,
            top_performers=[],
            market_gaps=[],
            recommendations=[]
        )
    
    # Calculate basic metrics
    prices = [c.current_price for c in competitors if c.current_price > 0]
    reviews = [c.review_count for c in competitors]
    ratings = [c.rating for c in competitors if c.rating > 0]
    
    avg_price = mean(prices) if prices else 0
    price_range = (min(prices), max(prices)) if prices else (0, 0)
    avg_reviews = mean(reviews) if reviews else 0
    avg_rating = mean(ratings) if ratings else 0
    
    # Determine market saturation
    high_review_products = len([c for c in competitors if c.review_count >= 100])
    if high_review_products >= len(competitors) * 0.7:
        market_saturation = "high"
    elif high_review_products >= len(competitors) * 0.3:
        market_saturation = "medium"
    else:
        market_saturation = "low"
    
    # Determine entry barriers
    strong_competitors = len([c for c in competitors if c.competitive_strength >= 70])
    if strong_competitors >= len(competitors) * 0.5:
        entry_barriers = "high"
    elif strong_competitors >= len(competitors) * 0.2:
        entry_barriers = "medium"
    else:
        entry_barriers = "low"
    
    # Calculate opportunity score
    opportunity_score = _calculate_opportunity_score(competitors, market_saturation, entry_barriers)
    
    # Get top performers
    top_performers = sorted(competitors, key=lambda c: c.competitive_strength, reverse=True)[:5]
    
    # Identify market gaps
    market_gaps = CompetitorAnalyzer.identify_market_gaps(competitors)
    
    # Generate recommendations
    recommendations = _generate_market_recommendations(competitors, market_saturation, entry_barriers)
    
    return MarketAnalysis(
        keyword=keyword,
        total_products=len(competitors),
        avg_price=avg_price,
        price_range=price_range,
        avg_reviews=avg_reviews,
        avg_rating=avg_rating,
        market_saturation=market_saturation,
        entry_barriers=entry_barriers,
        opportunity_score=opportunity_score,
        top_performers=top_performers,
        market_gaps=market_gaps,
        recommendations=recommendations
    )


def _calculate_opportunity_score(competitors: List[CompetitorMetrics], 
                                saturation: str, barriers: str) -> float:
    """Calculate market opportunity score (0-100)."""
    base_score = 50
    
    # Adjust for market saturation
    saturation_adjustments = {"low": 20, "medium": 0, "high": -20}
    base_score += saturation_adjustments.get(saturation, 0)
    
    # Adjust for entry barriers
    barrier_adjustments = {"low": 15, "medium": 0, "high": -15}
    base_score += barrier_adjustments.get(barriers, 0)
    
    # Adjust for competitor quality
    avg_strength = mean([c.competitive_strength for c in competitors]) if competitors else 50
    if avg_strength < 40:
        base_score += 15  # Weak competition = opportunity
    elif avg_strength > 70:
        base_score -= 10  # Strong competition = challenge
    
    # Adjust for market gaps
    gaps = CompetitorAnalyzer.identify_market_gaps(competitors)
    high_opportunity_gaps = len([g for g in gaps if g.get("opportunity") == "high"])
    base_score += high_opportunity_gaps * 5
    
    return max(0, min(100, base_score))


def _generate_market_insights(analysis: MarketAnalysis) -> List[str]:
    """Generate market-level insights."""
    insights = []
    
    # Market size insights
    if analysis.total_products >= 50:
        insights.append(f"Large market with {analysis.total_products} competing products")
    elif analysis.total_products >= 10:
        insights.append(f"Moderate market size with {analysis.total_products} competitors")
    else:
        insights.append(f"Small market with only {analysis.total_products} competitors")
    
    # Price insights
    if analysis.avg_price >= 15:
        insights.append(f"Premium market with average price of ${analysis.avg_price:.2f}")
    elif analysis.avg_price <= 8:
        insights.append(f"Budget market with average price of ${analysis.avg_price:.2f}")
    
    # Competition insights
    if analysis.market_saturation == "high":
        insights.append("Highly saturated market with established competitors")
    elif analysis.market_saturation == "low":
        insights.append("Emerging market with growth opportunities")
    
    # Opportunity insights
    if analysis.opportunity_score >= 70:
        insights.append("High opportunity market with good entry potential")
    elif analysis.opportunity_score <= 40:
        insights.append("Challenging market with limited opportunities")
    
    return insights


def _generate_market_recommendations(competitors: List[CompetitorMetrics], 
                                   saturation: str, barriers: str) -> List[str]:
    """Generate market-level recommendations."""
    recommendations = []
    
    # Entry strategy recommendations
    if barriers == "low" and saturation == "low":
        recommendations.append("Excellent market entry opportunity - move quickly to establish position")
    elif barriers == "high":
        recommendations.append("Consider niche differentiation or unique value proposition")
    
    # Pricing strategy recommendations
    if competitors:
        prices = [c.current_price for c in competitors if c.current_price > 0]
        if prices:
            min_price, max_price = min(prices), max(prices)
            if max_price - min_price > 10:
                recommendations.append(f"Wide price range (${min_price:.2f}-${max_price:.2f}) suggests segmentation opportunities")
    
    # Quality strategy recommendations
    low_rated = [c for c in competitors if c.rating < 4.0]
    if len(low_rated) > len(competitors) * 0.3:
        recommendations.append("Focus on quality to differentiate from poorly-rated competitors")
    
    # Market timing recommendations
    if saturation == "low":
        recommendations.append("Early market - focus on establishing brand and capturing market share")
    elif saturation == "high":
        recommendations.append("Mature market - focus on differentiation and niche targeting")
    
    return recommendations