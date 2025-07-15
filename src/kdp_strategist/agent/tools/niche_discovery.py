"""Niche Discovery Tool.

Finds profitable publishing niches by analyzing:
- Keyword variations and search volume
- Google Trends data for market interest
- Amazon competition analysis
- Market opportunity scoring
- Content gap identification

The tool combines multiple data sources to identify niches with:
- High market demand (Google Trends)
- Manageable competition (Amazon/Keepa data)
- Sustainable growth potential
- Clear monetization opportunities
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import itertools
import re

from ...data.cache_manager import CacheManager
from ...data.keepa_client import KeepaClient
from ...data.trends_client import TrendsClient
from ...models.niche_model import Niche
from ...models.trend_model import TrendAnalysis, TrendDirection, TrendStrength
from src.kdp_strategist.models.niche_model import Niche, CompetitionLevel, ProfitabilityTier, RiskLevel # Add RiskLevel
from src.kdp_strategist.models.trend_model import TrendAnalysis, TrendDirection, TrendStrength
logger = logging.getLogger(__name__)


class NicheScorer:
    """Scoring engine for niche profitability analysis."""

    # Scoring weights
    WEIGHTS = {
        "trend_score": 0.25,
        "competition_score": 0.30,
        "market_size_score": 0.20,
        "seasonality_score": 0.15,
        "content_gap_score": 0.10
    }

    # Competition scoring thresholds
    LOW_COMPETITION_THRESHOLD = 10
    MEDIUM_COMPETITION_THRESHOLD = 50
    HIGH_COMPETITION_THRESHOLD = 100

    HIGH_REVIEW_THRESHOLD = 1000
    MEDIUM_REVIEW_THRESHOLD = 100
    LOW_REVIEW_THRESHOLD = 10

    LOW_RATING_THRESHOLD = 3.5
    HIGH_RATING_THRESHOLD = 4.5
    
    @classmethod
    def calculate_profitability_score(cls, niche_data: Dict[str, Any]) -> float:
        """Calculate overall profitability score (0-100)."""
        scores = {
            "trend_score": cls._score_trend_strength(niche_data.get("trend_analysis")),
            "competition_score": cls._score_competition_level(niche_data.get("competition_data")),
            "market_size_score": cls._score_market_size(niche_data.get("market_metrics")),
            "seasonality_score": cls._score_seasonality(niche_data.get("seasonal_patterns")),
            "content_gap_score": cls._score_content_gaps(niche_data.get("content_analysis"))
        }
        
        # Calculate weighted score
        total_score = sum(score * cls.WEIGHTS[key] for key, score in scores.items() if score is not None)
        weight_sum = sum(cls.WEIGHTS[key] for key, score in scores.items() if score is not None)
        
        return (total_score / weight_sum * 100) if weight_sum > 0 else 0
    
    @staticmethod
    def _score_trend_strength(trend_analysis: Optional[TrendAnalysis]) -> Optional[float]:
        """Score based on trend strength and direction."""
        if not trend_analysis:
            return None
        
        base_score = trend_analysis.trend_score
        
        # Adjust for trend direction
        if trend_analysis.direction == TrendDirection.RISING:
            base_score *= 1.2
        elif trend_analysis.direction == TrendDirection.DECLINING:
            base_score *= 0.7
        
        # Adjust for trend strength
        strength_multipliers = {
            TrendStrength.VERY_STRONG: 1.3,
            TrendStrength.STRONG: 1.1,
            TrendStrength.MODERATE: 1.0,
            TrendStrength.WEAK: 0.8,
            TrendStrength.VERY_WEAK: 0.5
        }
        
        multiplier = strength_multipliers.get(trend_analysis.strength, 1.0)
        return min(100, base_score * multiplier)
    
    @staticmethod
    def _score_competition_level(competition_data: Optional[Dict[str, Any]]) -> Optional[float]:
        """Score based on competition analysis."""
        if not competition_data:
            return None
        
        # Lower competition = higher score
        competitor_count = competition_data.get("competitor_count", 0)
        avg_reviews = competition_data.get("avg_review_count", 0)
        avg_rating = competition_data.get("avg_rating", 0)
        price_range = competition_data.get("price_range", {})
        
        # Base score inversely related to competition
        if competitor_count == 0:
            base_score = 100
        elif competitor_count < cls.LOW_COMPETITION_THRESHOLD:
            base_score = 90
        elif competitor_count < cls.MEDIUM_COMPETITION_THRESHOLD:
            base_score = 70
        elif competitor_count < cls.HIGH_COMPETITION_THRESHOLD:
            base_score = 50
        else:
            base_score = 30

        # Adjust for review saturation
        if avg_reviews > cls.HIGH_REVIEW_THRESHOLD:
            base_score *= 0.6  # High review saturation
        elif avg_reviews > cls.MEDIUM_REVIEW_THRESHOLD:
            base_score *= 0.8
        elif avg_reviews < cls.LOW_REVIEW_THRESHOLD:
            base_score *= 1.2  # Low review saturation = opportunity

        # Adjust for rating quality
        if avg_rating < cls.LOW_RATING_THRESHOLD:
            base_score *= 1.3  # Poor ratings = opportunity
        elif avg_rating > cls.HIGH_RATING_THRESHOLD:
            base_score *= 0.9  # High ratings = strong competition
        
        return min(100, base_score)
    
    @staticmethod
    def _score_market_size(market_metrics: Optional[Dict[str, Any]]) -> Optional[float]:
        """Score based on market size indicators."""
        if not market_metrics:
            return None
        
        search_volume = market_metrics.get("estimated_search_volume", 0)
        related_keywords = market_metrics.get("related_keyword_count", 0)
        category_size = market_metrics.get("category_size_score", 50)
        
        # Score based on search volume
        if search_volume > 10000:
            volume_score = 90
        elif search_volume > 1000:
            volume_score = 70
        elif search_volume > 100:
            volume_score = 50
        else:
            volume_score = 30
        
        # Adjust for keyword diversity
        keyword_multiplier = min(1.5, 1 + (related_keywords / 100))
        
        # Combine scores
        final_score = (volume_score * 0.6 + category_size * 0.4) * keyword_multiplier
        return min(100, final_score)
    
    @staticmethod
    def _score_seasonality(seasonal_patterns: Optional[Dict[str, Any]]) -> Optional[float]:
        """Score based on seasonal stability."""
        if not seasonal_patterns:
            return 75  # Neutral score if no data
        
        seasonality_strength = seasonal_patterns.get("seasonality_strength", 0)
        peak_months = seasonal_patterns.get("peak_months", [])
        consistency = seasonal_patterns.get("consistency_score", 50)
        
        # Lower seasonality = higher score (more stable)
        if seasonality_strength < 10:
            base_score = 95  # Very stable
        elif seasonality_strength < 25:
            base_score = 80  # Moderately stable
        elif seasonality_strength < 50:
            base_score = 60  # Some seasonality
        else:
            base_score = 40  # Highly seasonal
        
        # Adjust for consistency
        consistency_multiplier = consistency / 100
        
        return base_score * consistency_multiplier
    
    @staticmethod
    def _score_content_gaps(content_analysis: Optional[Dict[str, Any]]) -> Optional[float]:
        """Score based on content gap opportunities."""
        if not content_analysis:
            return None
        
        gap_count = content_analysis.get("identified_gaps", 0)
        content_quality = content_analysis.get("avg_content_quality", 50)
        differentiation_opportunities = content_analysis.get("differentiation_score", 50)
        
        # More gaps = higher opportunity
        if gap_count > 10:
            gap_score = 90
        elif gap_count > 5:
            gap_score = 70
        elif gap_count > 2:
            gap_score = 50
        else:
            gap_score = 30
        
        # Lower content quality = higher opportunity
        quality_multiplier = (100 - content_quality) / 100
        
        # Combine scores
        final_score = (gap_score * 0.6 + differentiation_opportunities * 0.4) * (1 + quality_multiplier)
        return min(100, final_score)


class KeywordExpander:
    """Expands base keywords into niche-specific variations."""
    
    # Common keyword modifiers for publishing niches
    MODIFIERS = {
        "journal": ["journal", "notebook", "diary", "planner", "log", "tracker", "organizer"],
        "audience": ["kids", "children", "teens", "adults", "seniors", "women", "men", "professionals"],
        "purpose": ["daily", "weekly", "monthly", "travel", "work", "personal", "business", "creative"],
        "style": ["lined", "dotted", "blank", "guided", "prompted", "illustrated", "minimalist"],
        "theme": ["gratitude", "mindfulness", "fitness", "productivity", "self-care", "goals"]
    }
    
    @classmethod
    def expand_keywords(cls, base_keywords: List[str], max_combinations: int = 100) -> List[str]:
        """Expand base keywords into variations."""
        expanded = set(base_keywords)
        
        for base_keyword in base_keywords:
            # Add single modifier combinations
            for category, modifiers in cls.MODIFIERS.items():
                for modifier in modifiers:
                    # Prefix combinations
                    expanded.add(f"{modifier} {base_keyword}")
                    # Suffix combinations
                    expanded.add(f"{base_keyword} {modifier}")
            
            # Add two-modifier combinations (limited)
            modifier_pairs = list(itertools.combinations(cls.MODIFIERS.keys(), 2))
            for cat1, cat2 in modifier_pairs[:5]:  # Limit combinations
                for mod1 in cls.MODIFIERS[cat1][:3]:  # Top 3 from each category
                    for mod2 in cls.MODIFIERS[cat2][:3]:
                        expanded.add(f"{mod1} {base_keyword} {mod2}")
                        if len(expanded) >= max_combinations:
                            break
                    if len(expanded) >= max_combinations:
                        break
                if len(expanded) >= max_combinations:
                    break
        
        # Clean and filter keywords
        cleaned = []
        for keyword in expanded:
            # Basic cleaning
            keyword = re.sub(r'\s+', ' ', keyword.strip().lower())
            # Filter out very long keywords
            if len(keyword) <= 100 and len(keyword.split()) <= 6:
                cleaned.append(keyword)
        
        return cleaned[:max_combinations]


async def find_profitable_niches(
    trends_client: TrendsClient,
    keepa_client: Optional[KeepaClient],
    cache_manager: CacheManager,
    base_keywords: List[str],
    categories: Optional[List[str]] = None,
    min_profitability_score: float = 60,
    max_competition_level: str = "medium",
    limit: int = 10
) -> Dict[str, Any]:
    """Find profitable publishing niches.
    
    Args:
        trends_client: Google Trends client
        keepa_client: Keepa API client (optional)
        cache_manager: Cache manager for performance
        base_keywords: Starting keywords for niche discovery
        categories: Amazon categories to focus on
        min_profitability_score: Minimum score threshold (0-100)
        max_competition_level: Maximum competition level (low/medium/high)
        limit: Maximum number of niches to return
    
    Returns:
        Dictionary containing discovered niches and analysis metadata
    """
    logger.info(f"Starting niche discovery for keywords: {base_keywords}")
    
    try:
        # Step 1: Expand keywords
        expanded_keywords = KeywordExpander.expand_keywords(base_keywords, max_combinations=200)
        logger.info(f"Expanded to {len(expanded_keywords)} keyword variations")
        
        # Step 2: Analyze trends for expanded keywords (batch processing)
        trend_analyses = await _batch_analyze_trends(trends_client, expanded_keywords[:50])  # Limit for performance
        
        # Step 3: Filter keywords with good trend potential
        promising_keywords = _filter_promising_trends(trend_analyses, min_trend_score=30)
        logger.info(f"Found {len(promising_keywords)} keywords with good trend potential")
        
        # Step 4: Analyze competition for promising keywords
        competition_data = await _analyze_competition(keepa_client, promising_keywords, categories)
        
        # Step 5: Generate niche candidates
        niche_candidates = await _generate_niche_candidates(
            promising_keywords, trend_analyses, competition_data, categories
        )
        
        # Step 6: Score and rank niches
        scored_niches = _score_and_rank_niches(niche_candidates, min_profitability_score, max_competition_level)
        
        # Step 7: Return top niches
        top_niches = scored_niches[:limit]
        
        result = {
            "niches": [niche.to_dict() for niche in top_niches],
            "analysis_metadata": {
                "base_keywords": base_keywords,
                "expanded_keywords_count": len(expanded_keywords),
                "analyzed_trends_count": len(trend_analyses),
                "promising_keywords_count": len(promising_keywords),
                "niche_candidates_count": len(niche_candidates),
                "final_niches_count": len(top_niches),
                "min_profitability_score": min_profitability_score,
                "max_competition_level": max_competition_level,
                "analysis_timestamp": datetime.now().isoformat()
            },
            "recommendations": _generate_recommendations(top_niches, scored_niches)
        }
        
        logger.info(f"Niche discovery completed. Found {len(top_niches)} profitable niches")
        return result
    
    except Exception as e:
        logger.error(f"Niche discovery failed: {e}")
        raise


async def _batch_analyze_trends(trends_client: TrendsClient, keywords: List[str]) -> Dict[str, TrendAnalysis]:
    """Analyze trends for multiple keywords efficiently."""
    trend_analyses = {}
    
    # Process in smaller batches to respect rate limits
    batch_size = 5
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]
        
        # Process batch concurrently
        tasks = []
        for keyword in batch:
            task = trends_client.get_trend_analysis(keyword, timeframe="today 12-m")
            tasks.append(task)
        
        # Wait for batch completion
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for keyword, result in zip(batch, batch_results):
            if isinstance(result, TrendAnalysis):
                trend_analyses[keyword] = result
            elif isinstance(result, Exception):
                logger.warning(f"Failed to analyze trend for '{keyword}': {result}")
        
        # Rate limiting delay between batches
        if i + batch_size < len(keywords):
            await asyncio.sleep(2)
    
    return trend_analyses


def _filter_promising_trends(trend_analyses: Dict[str, TrendAnalysis], min_trend_score: float = 30) -> List[str]:
    """Filter keywords with promising trend characteristics."""
    promising = []
    
    for keyword, analysis in trend_analyses.items():
        # Basic trend score filter
        if analysis.trend_score < min_trend_score:
            continue
        
        # Avoid declining trends
        if analysis.direction == TrendDirection.DECLINING and analysis.trend_score < 50:
            continue
        
        # Require minimum confidence
        if analysis.confidence_level < 0.3:
            continue
        
        promising.append(keyword)
    
    return promising


async def _analyze_competition(keepa_client: Optional[KeepaClient], keywords: List[str], 
                              categories: Optional[List[str]]) -> Dict[str, Dict[str, Any]]:
    """Analyze competition for keywords using Amazon/Keepa data."""
    competition_data = {}
    
    if not keepa_client:
        logger.warning("No Keepa client available - using simulated competition data")
        # Return simulated data for development
        for keyword in keywords:
            competition_data[keyword] = {
                "competitor_count": len(keyword.split()) * 20,  # Rough estimate
                "avg_review_count": 50,
                "avg_rating": 4.0,
                "price_range": {"min": 5.99, "max": 19.99, "avg": 12.99},
                "estimated": True
            }
        return competition_data
    
    # Analyze competition using Keepa search
    for keyword in keywords[:20]:  # Limit for performance
        try:
            # Search for products
            products = keepa_client.search_products(keyword, limit=20)
            
            if products:
                # Analyze competition metrics
                review_counts = [p.review_count for p in products if p.review_count]
                ratings = [p.rating for p in products if p.rating]
                prices = [p.current_price for p in products if p.current_price]
                
                competition_data[keyword] = {
                    "competitor_count": len(products),
                    "avg_review_count": sum(review_counts) / len(review_counts) if review_counts else 0,
                    "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
                    "price_range": {
                        "min": min(prices) if prices else 0,
                        "max": max(prices) if prices else 0,
                        "avg": sum(prices) / len(prices) if prices else 0
                    },
                    "estimated": False
                }
            else:
                # No competition found
                competition_data[keyword] = {
                    "competitor_count": 0,
                    "avg_review_count": 0,
                    "avg_rating": 0,
                    "price_range": {"min": 0, "max": 0, "avg": 0},
                    "estimated": False
                }
        
        except Exception as e:
            logger.warning(f"Failed to analyze competition for '{keyword}': {e}")
            continue
    
    return competition_data


async def _generate_niche_candidates(keywords: List[str], trend_analyses: Dict[str, TrendAnalysis],
                                    competition_data: Dict[str, Dict[str, Any]], 
                                    categories: Optional[List[str]]) -> List[Niche]:
    """Generate niche candidates from analyzed data."""
    niche_candidates = []
    
    for keyword in keywords:
        trend_analysis = trend_analyses.get(keyword)
        competition = competition_data.get(keyword, {})
        
        if not trend_analysis:
            continue
        
        # Create niche object
    niche = Niche(
    category=categories[0] if categories else "Books & Journals",
    primary_keyword=keyword,
    keywords=[keyword] + trend_analysis.related_queries[:10],
    trend_analysis_data=trend_analysis, # Pass TrendAnalysis object directly
    competitor_analysis_data=competition, # Pass competitor data as dict
    market_size_score=_estimate_market_size(trend_analysis, competition),
    seasonal_factors=trend_analysis.seasonal_patterns,
        # Calculate and assign numeric scores directly during construction
    profitability_score_numeric=NicheScorer.calculate_profitability_score({
        "trend_analysis": trend_analysis,
        "competition_data": competition,
        "market_metrics": {"estimated_search_volume": _estimate_market_size(trend_analysis, competition) * 100},
        "seasonal_patterns": trend_analysis.seasonal_patterns,
        "content_analysis": {"identified_gaps": 5}
    }),
    competition_score_numeric=NicheScorer._score_competition_level(competition) or 0.0,
        # `competition_level` and `profitability_tier` will be set in Niche's __post_init__
    )
    niche_candidates.append(niche)
    
    return niche_candidates


def _estimate_market_size(trend_analysis: TrendAnalysis, competition_data: Dict[str, Any]) -> float:
    """Estimate market size score based on trend and competition data."""
    base_score = trend_analysis.trend_score
    
    # Adjust for competition level
    competitor_count = competition_data.get("competitor_count", 0)
    if competitor_count == 0:
        competition_multiplier = 1.5  # No competition = larger opportunity
    elif competitor_count < 10:
        competition_multiplier = 1.2
    elif competitor_count < 50:
        competition_multiplier = 1.0
    else:
        competition_multiplier = 0.8
    
    # Adjust for trend strength
    if trend_analysis.strength in [TrendStrength.STRONG, TrendStrength.VERY_STRONG]:
        strength_multiplier = 1.3
    elif trend_analysis.strength == TrendStrength.MODERATE:
        strength_multiplier = 1.0
    else:
        strength_multiplier = 0.7
    
    return min(100, base_score * competition_multiplier * strength_multiplier)


def _score_and_rank_niches(niche_candidates: List[Niche], min_score: float, 
                           max_competition: str) -> List[Niche]:
    """Score and rank niche candidates."""
    scored_niches = []
    
    competition_limits = {
        "low": 20,
        "medium": 50,
        "high": 100
    }
    
    max_competitors = competition_limits.get(max_competition, 50)
    
    for niche in niche_candidates:
        # Re-calculate or confirm numeric competition score
        niche.competition_score_numeric = NicheScorer._score_competition_level(niche.competitor_analysis_data) or 0.0

        # Set the categorical competition level based on numeric score
        niche.competition_level = Niche._determine_competition_level(niche.competition_score_numeric)

        # Calculate the numeric profitability score (ensure it uses the renamed fields internally)
        niche_data_for_scoring = {
            "trend_analysis": niche.trend_analysis_data,
            "competition_data": niche.competitor_analysis_data,
            "market_metrics": {"estimated_search_volume": niche.market_size_score * 100},
            "seasonal_patterns": niche.seasonal_factors,
            "content_analysis": {"identified_gaps": 5}
        }
        niche.profitability_score_numeric = NicheScorer.calculate_profitability_score(niche_data_for_scoring)

        # Set the categorical profitability tier based on numeric score
        niche.profitability_tier = Niche._determine_profitability_tier(niche.profitability_score_numeric)

        # Apply minimum score filter (using numeric score)
        if niche.profitability_score_numeric >= min_score:
            scored_niches.append(niche)

    # Sort by profitability score_numeric (descending)
    scored_niches.sort(key=lambda n: n.profitability_score_numeric, reverse=True)
    
    return scored_niches


def _generate_recommendations(top_niches: List[Niche], all_scored_niches: List[Niche]) -> Dict[str, Any]:
    """Generate actionable recommendations based on niche analysis."""
    if not top_niches:
        return {"message": "No profitable niches found with current criteria"}
    
    best_niche = top_niches[0]
    
    recommendations = {
        "primary_recommendation": {
            "niche": best_niche.primary_keyword,
            "score": best_niche.profitability_score_numeric, # Use numeric score
            "reason": f"Highest profitability score with {best_niche.competition_level.value} competition" # Use enum .value
        },
        "quick_wins": [],
        "long_term_opportunities": [],
        "market_insights": {
            "avg_profitability_score": sum(n.profitability_score_numeric for n in all_scored_niches) / len(all_scored_niches),
            "competition_distribution": {
                "low": len([n for n in all_scored_niches if n.competition_level == CompetitionLevel.LOW]),
                "medium": len([n for n in all_scored_niches if n.competition_level == CompetitionLevel.MEDIUM]),
                "high": len([n for n in all_scored_niches if n.competition_level == CompetitionLevel.HIGH])
            }
        }
    }
    
    # Identify quick wins (low competition, decent score)
    for niche in top_niches[:5]:
        if niche.competition_level == CompetitionLevel.LOW and niche.profitability_score_numeric >= 60:
            recommendations["quick_wins"].append({
                "niche": niche.primary_keyword,
                "score": niche.profitability_score,
                "competitors": niche.competitor_data.get("count", 0)
            })
    
    # Identify long-term opportunities (high potential, manageable competition)
    for niche in top_niches[:10]:
        if (niche.profitability_score_numeric >= 75 and
            niche.trend_analysis_data and # Use the renamed field
            niche.trend_analysis_data.direction == TrendDirection.RISING):
            recommendations["long_term_opportunities"].append({
                "niche": niche.primary_keyword,
                "score": niche.profitability_score,
                "trend_direction": niche.trend_analysis.direction.value
            })
    
    return recommendations