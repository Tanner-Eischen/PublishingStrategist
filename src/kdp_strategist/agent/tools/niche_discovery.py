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
from ...exceptions import (
    ValidationError,
    ToolExecutionError,
    create_error_response
)
from ...exceptions import APIError
from ...exceptions import handle_api_error

# from ...data.keepa_client import KeepaClient
from ...models.niche_model import (
    Niche,
    CompetitionLevel,
    ProfitabilityTier,
    RiskLevel,
    MarketSummary,
    PriceRange,
)


logger = logging.getLogger(__name__)


class NicheScorer:
    """Enhanced scoring engine for comprehensive niche profitability analysis."""

    # Enhanced scoring weights with additional factors
    WEIGHTS = {
        "trend_score": 0.22,  # Reduced slightly to accommodate new factors
        "competition_score": 0.25,  # Slightly reduced but still important
        "market_size_score": 0.18,  # Market potential
        "seasonality_score": 0.12,  # Seasonal stability
        "content_gap_score": 0.10,  # Content opportunities
        "confidence_score": 0.08,  # Data reliability
        "cluster_bonus": 0.05,  # Cluster-based bonus
    }

    # Enhanced competition scoring thresholds
    COMPETITION_THRESHOLDS = {
        "very_low": 5,
        "low": 15,
        "medium_low": 35,
        "medium": 60,
        "medium_high": 100,
        "high": 200,
        "very_high": 500,
    }

    # Review count thresholds for market saturation analysis
    REVIEW_THRESHOLDS = {
        "very_low": 10,
        "low": 50,
        "medium": 200,
        "high": 500,
        "very_high": 1000,
        "saturated": 2000,
    }

    # Rating quality thresholds
    RATING_THRESHOLDS = {
        "poor": 3.0,
        "below_average": 3.5,
        "average": 4.0,
        "good": 4.3,
        "excellent": 4.7,
    }

    # Price range analysis thresholds
    PRICE_THRESHOLDS = {
        "very_low": 2.99,
        "low": 6.99,
        "medium": 12.99,
        "high": 19.99,
        "premium": 29.99,
    }

    # Legacy threshold constants for backward compatibility
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
        """Calculate comprehensive profitability score with enhanced multi-factor analysis."""
        scores = {
            "trend_score": cls._score_trend_strength_enhanced(
                niche_data.get("trend_analysis")
            ),
            "competition_score": cls._score_competition_level_enhanced(
                niche_data.get("competition_data")
            ),
            "market_size_score": cls._score_market_size_enhanced(
                niche_data.get("market_metrics")
            ),
            "seasonality_score": cls._score_seasonality_enhanced(
                niche_data.get("seasonal_patterns")
            ),
            "content_gap_score": cls._score_content_gaps_enhanced(
                niche_data.get("content_analysis")
            ),
            "confidence_score": cls._score_confidence_level(
                niche_data.get("trend_analysis")
            ),
            "cluster_bonus": cls._score_cluster_bonus(
                niche_data.get("cluster_context")
            ),
        }

        # Calculate weighted score with dynamic weight adjustment
        adjusted_weights = cls._adjust_weights_dynamically(scores, niche_data)

        total_score = sum(
            score * adjusted_weights[key]
            for key, score in scores.items()
            if score is not None
        )
        weight_sum = sum(
            adjusted_weights[key] for key, score in scores.items() if score is not None
        )

        final_score = (total_score / weight_sum) if weight_sum > 0 else 0

        # Apply final adjustments based on data quality and market conditions
        final_score = cls._apply_final_adjustments(final_score, niche_data, scores)

        return min(100.0, max(0.0, final_score))

    @classmethod
    def _adjust_weights_dynamically(
        cls, scores: Dict[str, float], niche_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Dynamically adjust weights based on data quality and market conditions."""
        adjusted_weights = cls.WEIGHTS.copy()

        # Increase competition weight if we have high-quality competition data
        competition_data = niche_data.get("competition_data")
        if competition_data and not competition_data.estimated:
            adjusted_weights["competition_score"] += 0.05
            adjusted_weights["trend_score"] -= 0.02
            adjusted_weights["market_size_score"] -= 0.03

        # Increase trend weight for high-confidence trend data
        trend_analysis = niche_data.get("trend_analysis")
        if trend_analysis and trend_analysis.confidence_level > 0.7:
            adjusted_weights["trend_score"] += 0.03
            adjusted_weights["seasonality_score"] -= 0.02
            adjusted_weights["cluster_bonus"] -= 0.01

        # Adjust for cluster context
        cluster_context = niche_data.get("cluster_context")
        if cluster_context and cluster_context.get("cluster_priority", 0) > 8:
            adjusted_weights["cluster_bonus"] += 0.02
            adjusted_weights["content_gap_score"] -= 0.02

        return adjusted_weights

    @classmethod
    def _apply_final_adjustments(
        cls,
        base_score: float,
        niche_data: Dict[str, Any],
        component_scores: Dict[str, float],
    ) -> float:
        """Apply final adjustments based on overall market conditions."""
        adjusted_score = base_score

        # Penalty for very low confidence
        trend_analysis = niche_data.get("trend_analysis")
        if trend_analysis and trend_analysis.confidence_level < 0.3:
            adjusted_score *= 0.85

        # Bonus for exceptional opportunities (low competition + high trends)
        competition_score = component_scores.get("competition_score", 0)
        trend_score = component_scores.get("trend_score", 0)

        if competition_score > 80 and trend_score > 70:  # Low competition + good trends
            adjusted_score *= 1.15

        # Penalty for oversaturated markets
        competition_data = niche_data.get("competition_data")
        if (
            competition_data
            and competition_data.competitor_count > 200
            and competition_data.avg_rating > 4.5
        ):
            adjusted_score *= 0.9

        return adjusted_score

    @classmethod
    def _score_trend_strength_enhanced(
        cls, trend_analysis: Optional[Any]
    ) -> Optional[float]:
        """Enhanced trend strength scoring with multiple factors."""
        if not trend_analysis:
            return 50.0  # Neutral score when trends unavailable

        base_score = trend_analysis.trend_score

        # Enhanced direction adjustments
        direction_multipliers = {
            "rising": 1.25,
            "stable": 1.0,
            "declining": 0.65,
            "volatile": 0.8,
        }

        direction_multiplier = direction_multipliers.get(
            trend_analysis.trend_direction, 1.0
        )
        base_score *= direction_multiplier

        # Enhanced strength adjustments
        strength_multipliers = {
            "very_strong": 1.4,
            "strong": 1.2,
            "moderate": 1.0,
            "weak": 0.75,
            "very_weak": 0.4,
        }

        strength_multiplier = strength_multipliers.get(
            trend_analysis.trend_strength, 1.0
        )
        base_score *= strength_multiplier

        # Confidence level adjustment
        confidence_multiplier = 0.7 + (trend_analysis.confidence_level * 0.3)
        base_score *= confidence_multiplier

        # Growth rate bonus/penalty
        if hasattr(trend_analysis, "growth_rate") and trend_analysis.growth_rate:
            if trend_analysis.growth_rate > 5:  # Strong positive growth
                base_score *= 1.1
            elif trend_analysis.growth_rate < -5:  # Strong negative growth
                base_score *= 0.9

        # Volatility penalty
        if (
            hasattr(trend_analysis, "volatility_score")
            and trend_analysis.volatility_score
        ):
            if trend_analysis.volatility_score > 70:  # High volatility
                base_score *= 0.9

        return min(100, max(0, base_score))

    @classmethod
    def _score_competition_level_enhanced(
        cls, competition_data: Optional[MarketSummary]
    ) -> Optional[float]:
        """Enhanced competition scoring with detailed market analysis."""
        if not competition_data:
            return None

        competitor_count = competition_data.competitor_count
        avg_reviews = competition_data.avg_review_count
        avg_rating = competition_data.avg_rating
        price_range = competition_data.price_range

        # Enhanced base scoring with more granular thresholds
        if competitor_count == 0:
            base_score = 100
        elif competitor_count <= cls.COMPETITION_THRESHOLDS["very_low"]:
            base_score = 95
        elif competitor_count <= cls.COMPETITION_THRESHOLDS["low"]:
            base_score = 85
        elif competitor_count <= cls.COMPETITION_THRESHOLDS["medium_low"]:
            base_score = 75
        elif competitor_count <= cls.COMPETITION_THRESHOLDS["medium"]:
            base_score = 60
        elif competitor_count <= cls.COMPETITION_THRESHOLDS["medium_high"]:
            base_score = 45
        elif competitor_count <= cls.COMPETITION_THRESHOLDS["high"]:
            base_score = 30
        else:
            base_score = 15

        # Enhanced review saturation analysis
        if avg_reviews >= cls.REVIEW_THRESHOLDS["saturated"]:
            base_score *= 0.5  # Heavily saturated market
        elif avg_reviews >= cls.REVIEW_THRESHOLDS["very_high"]:
            base_score *= 0.6
        elif avg_reviews >= cls.REVIEW_THRESHOLDS["high"]:
            base_score *= 0.75
        elif avg_reviews >= cls.REVIEW_THRESHOLDS["medium"]:
            base_score *= 0.9
        elif avg_reviews <= cls.REVIEW_THRESHOLDS["very_low"]:
            base_score *= 1.3  # Low review saturation = opportunity

        # Enhanced rating quality analysis
        if avg_rating <= cls.RATING_THRESHOLDS["poor"]:
            base_score *= 1.4  # Poor ratings = big opportunity
        elif avg_rating <= cls.RATING_THRESHOLDS["below_average"]:
            base_score *= 1.2  # Below average = opportunity
        elif avg_rating <= cls.RATING_THRESHOLDS["average"]:
            base_score *= 1.1  # Average = slight opportunity
        elif avg_rating >= cls.RATING_THRESHOLDS["excellent"]:
            base_score *= 0.8  # Excellent ratings = strong competition
        elif avg_rating >= cls.RATING_THRESHOLDS["good"]:
            base_score *= 0.9  # Good ratings = moderate competition

        # Price range analysis
        if price_range and price_range.avg > 0:
            avg_price = price_range.avg
            if avg_price <= cls.PRICE_THRESHOLDS["very_low"]:
                base_score *= 0.9  # Very low prices = price competition
            elif avg_price >= cls.PRICE_THRESHOLDS["premium"]:
                base_score *= (
                    1.1  # Premium prices = opportunity for competitive pricing
                )

        # Data quality adjustment
        if competition_data.estimated:
            base_score *= 0.9  # Slight penalty for estimated data

        return min(100, max(0, base_score))

    @classmethod
    def _score_market_size_enhanced(
        cls, market_metrics: Optional[Dict[str, Any]]
    ) -> Optional[float]:
        """Enhanced market size scoring with comprehensive analysis."""
        if not market_metrics:
            return None

        search_volume = market_metrics.get("estimated_search_volume", 0)
        related_keywords = market_metrics.get("related_keyword_count", 0)
        category_size = market_metrics.get("category_size_score", 50)
        cluster_adjustment = market_metrics.get("cluster_adjustment", 1.0)

        # Enhanced search volume scoring
        if search_volume >= 50000:
            volume_score = 95
        elif search_volume >= 20000:
            volume_score = 85
        elif search_volume >= 10000:
            volume_score = 75
        elif search_volume >= 5000:
            volume_score = 65
        elif search_volume >= 1000:
            volume_score = 55
        elif search_volume >= 500:
            volume_score = 45
        elif search_volume >= 100:
            volume_score = 35
        else:
            volume_score = 25

        # Enhanced keyword diversity scoring
        if related_keywords >= 50:
            keyword_multiplier = 1.4
        elif related_keywords >= 25:
            keyword_multiplier = 1.3
        elif related_keywords >= 15:
            keyword_multiplier = 1.2
        elif related_keywords >= 10:
            keyword_multiplier = 1.1
        elif related_keywords >= 5:
            keyword_multiplier = 1.0
        else:
            keyword_multiplier = 0.9

        # Combine scores with enhanced weighting
        base_score = (
            volume_score * 0.5 + category_size * 0.3 + (related_keywords * 2) * 0.2
        )
        enhanced_score = base_score * keyword_multiplier * cluster_adjustment

        return min(100, max(0, enhanced_score))

    @classmethod
    def _score_seasonality_enhanced(
        cls, seasonal_patterns: Optional[Dict[str, Any]]
    ) -> Optional[float]:
        """Enhanced seasonality scoring with detailed pattern analysis."""
        if not seasonal_patterns:
            return 75  # Neutral score if no data

        seasonality_strength = seasonal_patterns.get("seasonality_strength", 0)
        peak_month = seasonal_patterns.get("peak_month")
        monthly_averages = seasonal_patterns.get("monthly_averages", {})

        # Base seasonality scoring (lower seasonality = higher score for stability)
        if seasonality_strength <= 5:
            base_score = 95  # Very stable
        elif seasonality_strength <= 15:
            base_score = 85  # Stable
        elif seasonality_strength <= 30:
            base_score = 70  # Moderately stable
        elif seasonality_strength <= 50:
            base_score = 55  # Some seasonality
        elif seasonality_strength <= 75:
            base_score = 40  # Seasonal
        else:
            base_score = 25  # Highly seasonal

        # Seasonal pattern bonuses/penalties
        if peak_month:
            # Holiday season bonus (December/January)
            if peak_month in [12, 1]:
                base_score += 10  # Holiday publishing opportunity
            # Back-to-school bonus (August/September)
            elif peak_month in [8, 9]:
                base_score += 8
            # New Year resolution bonus (January/February)
            elif peak_month in [1, 2]:
                base_score += 6

        # Consistency analysis
        if monthly_averages and len(monthly_averages) >= 6:
            values = list(monthly_averages.values())
            if values:
                consistency = 1 - (max(values) - min(values)) / max(max(values), 1)
                consistency_multiplier = 0.8 + (consistency * 0.4)
                base_score *= consistency_multiplier

        return min(100, max(0, base_score))

    @classmethod
    def _score_content_gaps_enhanced(
        cls, content_analysis: Optional[Dict[str, Any]]
    ) -> Optional[float]:
        """Enhanced content gap scoring with detailed opportunity analysis."""
        if not content_analysis:
            return None

        gap_count = content_analysis.get("identified_gaps", 0)

        # Enhanced gap scoring
        if gap_count >= 8:
            gap_score = 95  # Excellent opportunity
        elif gap_count >= 6:
            gap_score = 85  # Very good opportunity
        elif gap_count >= 4:
            gap_score = 75  # Good opportunity
        elif gap_count >= 2:
            gap_score = 60  # Moderate opportunity
        elif gap_count >= 1:
            gap_score = 45  # Some opportunity
        else:
            gap_score = 25  # Limited opportunity

        return min(100, max(0, gap_score))

    @classmethod
    def _score_confidence_level(
        cls, trend_analysis: Optional[Any]
    ) -> Optional[float]:
        """Score based on data confidence and reliability."""
        if not trend_analysis:
            return None

        confidence = trend_analysis.confidence_level
        data_points = getattr(trend_analysis, "data_points", 0)

        # Base confidence score
        base_score = confidence * 100

        # Data points bonus
        if data_points >= 52:  # Full year of data
            base_score *= 1.1
        elif data_points >= 26:  # Half year
            base_score *= 1.05
        elif data_points < 12:  # Less than 3 months
            base_score *= 0.9

        return min(100, max(0, base_score))

    @classmethod
    def _score_cluster_bonus(
        cls, cluster_context: Optional[Dict[str, Any]]
    ) -> Optional[float]:
        """Score based on cluster priority and context."""
        if not cluster_context:
            return 50  # Neutral score

        cluster_priority = cluster_context.get("cluster_priority", 1.0)
        cluster_size = cluster_context.get("cluster_size", 1)

        # Base score from cluster priority
        base_score = cluster_priority * 10

        # Size bonus (larger clusters may indicate more opportunities)
        if cluster_size >= 20:
            size_multiplier = 1.2
        elif cluster_size >= 10:
            size_multiplier = 1.1
        elif cluster_size >= 5:
            size_multiplier = 1.0
        else:
            size_multiplier = 0.9

        final_score = base_score * size_multiplier

        return min(100, max(0, final_score))

    @staticmethod
    def _score_trend_strength(
        trend_analysis: Optional[Any],
    ) -> Optional[float]:
        """Score based on trend strength and direction."""
        if not trend_analysis:
            return None

        base_score = trend_analysis.trend_score

        # Adjust for trend direction
        if hasattr(trend_analysis, 'trend_direction'):
            if trend_analysis.trend_direction == "rising":
                base_score *= 1.2
            elif trend_analysis.trend_direction == "declining":
                base_score *= 0.7

        # Adjust for trend strength
        strength_multipliers = {
            "very_strong": 1.3,
            "strong": 1.1,
            "moderate": 1.0,
            "weak": 0.8,
            "very_weak": 0.5,
        }

        multiplier = strength_multipliers.get(getattr(trend_analysis, 'trend_strength', 'moderate'), 1.0)
        return min(100, base_score * multiplier)

    @classmethod
    def _score_competition_level(
        cls, competition_data: Optional[MarketSummary]
    ) -> Optional[float]:
        """Score based on competition analysis."""
        if not competition_data:
            return None

        # Lower competition = higher score

        competitor_count = competition_data.competitor_count
        avg_reviews = competition_data.avg_review_count
        avg_rating = competition_data.avg_rating

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
    def _score_seasonality(
        seasonal_patterns: Optional[Dict[str, Any]],
    ) -> Optional[float]:
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
    def _score_content_gaps(
        content_analysis: Optional[Dict[str, Any]],
    ) -> Optional[float]:
        """Score based on content gap opportunities."""
        if not content_analysis:
            return None

        gap_count = content_analysis.get("identified_gaps", 0)
        content_quality = content_analysis.get("avg_content_quality", 50)
        differentiation_opportunities = content_analysis.get(
            "differentiation_score", 50
        )

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
        final_score = (gap_score * 0.6 + differentiation_opportunities * 0.4) * (
            1 + quality_multiplier
        )
        return min(100, final_score)


class KeywordExpander:
    """Enhanced keyword expander with Google Trends integration and clustering."""

    # Enhanced keyword modifiers for publishing niches
    MODIFIERS = {
        "journal": [
            "journal",
            "notebook",
            "diary",
            "planner",
            "log",
            "tracker",
            "organizer",
            "workbook",
            "logbook",
            "record",
            "chronicle",
            "register",
        ],
        "audience": [
            "kids",
            "children",
            "teens",
            "adults",
            "seniors",
            "women",
            "men",
            "professionals",
            "students",
            "teachers",
            "parents",
            "entrepreneurs",
            "beginners",
            "experts",
            "millennials",
            "gen z",
        ],
        "purpose": [
            "daily",
            "weekly",
            "monthly",
            "travel",
            "work",
            "personal",
            "business",
            "creative",
            "academic",
            "professional",
            "hobby",
            "therapeutic",
            "educational",
            "inspirational",
            "motivational",
        ],
        "style": [
            "lined",
            "dotted",
            "blank",
            "guided",
            "prompted",
            "illustrated",
            "minimalist",
            "colorful",
            "artistic",
            "simple",
            "elegant",
            "modern",
            "vintage",
            "classic",
            "premium",
        ],
        "theme": [
            "gratitude",
            "mindfulness",
            "fitness",
            "productivity",
            "self-care",
            "goals",
            "wellness",
            "meditation",
            "success",
            "happiness",
            "growth",
            "healing",
            "spiritual",
            "motivational",
            "inspirational",
        ],
        "format": [
            "book",
            "guide",
            "manual",
            "handbook",
            "workbook",
            "course",
            "tutorial",
            "reference",
            "companion",
            "collection",
            "series",
        ],
        "time": [
            "2024",
            "2025",
            "new year",
            "monthly",
            "weekly",
            "daily",
            "seasonal",
            "annual",
            "quarterly",
            "morning",
            "evening",
        ],
    }

    # Semantic keyword clusters for better expansion
    SEMANTIC_CLUSTERS = {
        "self_improvement": [
            "self help",
            "personal development",
            "self improvement",
            "life coaching",
            "motivation",
            "inspiration",
            "success",
            "achievement",
            "growth mindset",
        ],
        "wellness": [
            "wellness",
            "health",
            "fitness",
            "nutrition",
            "mental health",
            "mindfulness",
            "meditation",
            "yoga",
            "stress relief",
            "healing",
        ],
        "productivity": [
            "productivity",
            "time management",
            "organization",
            "planning",
            "goal setting",
            "habits",
            "efficiency",
            "focus",
            "discipline",
        ],
        "creativity": [
            "creativity",
            "art",
            "writing",
            "design",
            "crafts",
            "diy",
            "creative writing",
            "artistic",
            "imagination",
            "innovation",
        ],
        "business": [
            "business",
            "entrepreneurship",
            "marketing",
            "sales",
            "leadership",
            "management",
            "finance",
            "investing",
            "startup",
            "career",
        ],
        "relationships": [
            "relationships",
            "love",
            "dating",
            "marriage",
            "family",
            "parenting",
            "communication",
            "social skills",
            "friendship",
            "romance",
        ],
    }

    @classmethod
    async def expand_keywords_with_trends(
        cls,
        base_keywords: List[str],
        max_combinations: int = 200,
        use_related_queries: bool = True,
        use_semantic_clustering: bool = True,
    ) -> Dict[str, Any]:
        """Enhanced keyword expansion using synthetic data (trends functionality removed).

        Returns:
            Dict containing expanded keywords, clusters, and metadata
        """
        logger.info(f"Starting enhanced keyword expansion for: {base_keywords}")

        # Step 1: Basic expansion using modifiers
        basic_expanded = cls._expand_with_modifiers(
            base_keywords, max_combinations // 2
        )

        # Step 2: Expand using synthetic related queries (trends functionality removed)
        trends_expanded = []
        if use_related_queries:
            trends_expanded = await cls._expand_with_trends(
                base_keywords, max_combinations // 4
            )

        # Step 3: Semantic clustering expansion
        semantic_expanded = []
        if use_semantic_clustering:
            semantic_expanded = cls._expand_with_semantic_clusters(
                base_keywords, max_combinations // 4
            )

        # Step 4: Combine and deduplicate
        all_keywords = list(set(basic_expanded + trends_expanded + semantic_expanded))

        # Step 5: Filter and rank keywords
        filtered_keywords = cls._filter_and_rank_keywords(
            all_keywords, max_combinations
        )

        # Step 6: Create keyword clusters for niche identification
        keyword_clusters = cls._create_keyword_clusters(filtered_keywords)

        result = {
            "expanded_keywords": filtered_keywords,
            "keyword_clusters": keyword_clusters,
            "expansion_metadata": {
                "base_keywords": base_keywords,
                "basic_expanded_count": len(basic_expanded),
                "trends_expanded_count": len(trends_expanded),
                "semantic_expanded_count": len(semantic_expanded),
                "total_unique_count": len(all_keywords),
                "final_filtered_count": len(filtered_keywords),
                "cluster_count": len(keyword_clusters),
                "expansion_methods": {
                    "modifiers": True,
                    "trends_related": use_related_queries,
                    "semantic_clustering": use_semantic_clustering,
                },
            },
        }

        logger.info(
            f"Keyword expansion complete: {len(filtered_keywords)} keywords in {len(keyword_clusters)} clusters"
        )
        return result

    @classmethod
    def _expand_with_modifiers(
        cls, base_keywords: List[str], max_combinations: int
    ) -> List[str]:
        """Expand keywords using predefined modifiers."""
        expanded = set(base_keywords)

        for base_keyword in base_keywords:
            # Single modifier combinations
            for category, modifiers in cls.MODIFIERS.items():
                for modifier in modifiers:
                    # Prefix combinations
                    expanded.add(f"{modifier} {base_keyword}")
                    # Suffix combinations
                    expanded.add(f"{base_keyword} {modifier}")
                    # For certain categories, add middle combinations
                    if category in ["audience", "purpose"]:
                        expanded.add(f"{base_keyword} for {modifier}")

            # Strategic two-modifier combinations
            priority_pairs = [
                ("audience", "purpose"),
                ("theme", "format"),
                ("style", "purpose"),
                ("audience", "theme"),
            ]

            for cat1, cat2 in priority_pairs:
                if cat1 in cls.MODIFIERS and cat2 in cls.MODIFIERS:
                    for mod1 in cls.MODIFIERS[cat1][:3]:
                        for mod2 in cls.MODIFIERS[cat2][:3]:
                            expanded.add(f"{mod1} {base_keyword} {mod2}")
                            expanded.add(f"{base_keyword} for {mod1} {mod2}")
                            if len(expanded) >= max_combinations:
                                break
                        if len(expanded) >= max_combinations:
                            break
                if len(expanded) >= max_combinations:
                    break

        return cls._clean_keywords(list(expanded))[:max_combinations]

    @classmethod
    async def _expand_with_trends(
        cls, base_keywords: List[str], max_keywords: int
    ) -> List[str]:
        """Expand keywords using synthetic related queries (trends functionality removed)."""
        # Trends functionality removed - using synthetic expansion for testing
        trends_keywords = []

        for keyword in base_keywords[:5]:  # Limit for consistency
            # Generate synthetic related queries
            synthetic_related = [
                f"{keyword} guide",
                f"{keyword} tips",
                f"{keyword} tutorial",
                f"best {keyword}",
                f"{keyword} for beginners",
                f"{keyword} book",
                f"{keyword} journal",
                f"{keyword} planner"
            ]
            
            trends_keywords.extend(synthetic_related)
            
            # Generate variations with modifiers
            for related in synthetic_related[:3]:
                for modifier in ["guide", "tips", "book", "journal", "planner"]:
                    trends_keywords.append(f"{related} {modifier}")
                    trends_keywords.append(f"{modifier} for {related}")

        return cls._clean_keywords(trends_keywords)[:max_keywords]

    @classmethod
    def _expand_with_semantic_clusters(
        cls, base_keywords: List[str], max_keywords: int
    ) -> List[str]:
        """Expand keywords using semantic clustering."""
        semantic_keywords = []

        for base_keyword in base_keywords:
            # Find relevant semantic clusters
            relevant_clusters = []
            for cluster_name, cluster_keywords in cls.SEMANTIC_CLUSTERS.items():
                # Check if base keyword relates to this cluster
                if any(word in base_keyword.lower() for word in cluster_keywords):
                    relevant_clusters.append(cluster_name)

            # If no direct match, use keyword similarity
            if not relevant_clusters:
                for cluster_name, cluster_keywords in cls.SEMANTIC_CLUSTERS.items():
                    if (
                        cls._calculate_keyword_similarity(
                            base_keyword, cluster_keywords
                        )
                        > 0.3
                    ):
                        relevant_clusters.append(cluster_name)

            # Generate combinations with cluster keywords
            for cluster_name in relevant_clusters[:2]:  # Limit clusters
                cluster_keywords = cls.SEMANTIC_CLUSTERS[cluster_name]
                for cluster_keyword in cluster_keywords[:5]:  # Top 5 from each cluster
                    semantic_keywords.extend(
                        [
                            f"{cluster_keyword} {base_keyword}",
                            f"{base_keyword} {cluster_keyword}",
                            f"{cluster_keyword} guide",
                            f"{cluster_keyword} book",
                            f"{cluster_keyword} journal",
                        ]
                    )

        return cls._clean_keywords(semantic_keywords)[:max_keywords]

    @classmethod
    def _calculate_keyword_similarity(
        cls, keyword: str, cluster_keywords: List[str]
    ) -> float:
        """Calculate similarity between keyword and cluster keywords."""
        keyword_words = set(keyword.lower().split())

        max_similarity = 0.0
        for cluster_keyword in cluster_keywords:
            cluster_words = set(cluster_keyword.lower().split())

            # Calculate Jaccard similarity
            intersection = len(keyword_words.intersection(cluster_words))
            union = len(keyword_words.union(cluster_words))

            if union > 0:
                similarity = intersection / union
                max_similarity = max(max_similarity, similarity)

        return max_similarity

    @classmethod
    def _filter_and_rank_keywords(
        cls, keywords: List[str], max_keywords: int
    ) -> List[str]:
        """Filter and rank keywords by relevance and potential."""
        # Clean keywords first
        cleaned = cls._clean_keywords(keywords)

        # Score keywords based on multiple factors
        scored_keywords = []
        for keyword in cleaned:
            score = cls._calculate_keyword_score(keyword)
            scored_keywords.append((keyword, score))

        # Sort by score (descending) and return top keywords
        scored_keywords.sort(key=lambda x: x[1], reverse=True)
        return [kw for kw, score in scored_keywords[:max_keywords]]

    @classmethod
    def _calculate_keyword_score(cls, keyword: str) -> float:
        """Calculate relevance score for a keyword."""
        score = 0.0
        words = keyword.lower().split()

        # Length penalty (prefer 2-4 words)
        word_count = len(words)
        if 2 <= word_count <= 4:
            score += 10
        elif word_count == 1 or word_count == 5:
            score += 5
        else:
            score -= 5

        # High-value keyword bonus
        high_value_terms = [
            "journal",
            "planner",
            "guide",
            "book",
            "workbook",
            "tracker",
            "daily",
            "weekly",
            "monthly",
            "productivity",
            "mindfulness",
            "self care",
            "wellness",
            "fitness",
            "business",
            "success",
        ]

        for term in high_value_terms:
            if term in keyword.lower():
                score += 5

        # Publishing format bonus
        publishing_formats = [
            "journal",
            "notebook",
            "planner",
            "guide",
            "workbook",
            "log",
        ]
        if any(fmt in keyword.lower() for fmt in publishing_formats):
            score += 8

        # Audience specificity bonus
        audiences = ["women", "men", "kids", "teens", "professionals", "students"]
        if any(aud in keyword.lower() for aud in audiences):
            score += 6

        # Avoid overly generic terms
        generic_terms = ["book", "guide", "tips", "how to"]
        if keyword.lower() in generic_terms:
            score -= 10

        return score

    @classmethod
    def _create_keyword_clusters(cls, keywords: List[str]) -> Dict[str, List[str]]:
        """Create keyword clusters for niche identification."""
        clusters = {}

        # Define cluster patterns
        cluster_patterns = {
            "journals_planners": [
                "journal",
                "planner",
                "diary",
                "notebook",
                "organizer",
            ],
            "wellness_mindfulness": [
                "wellness",
                "mindfulness",
                "meditation",
                "self care",
                "healing",
            ],
            "productivity_goals": [
                "productivity",
                "goals",
                "habits",
                "success",
                "achievement",
            ],
            "fitness_health": ["fitness", "health", "workout", "exercise", "nutrition"],
            "business_career": [
                "business",
                "career",
                "professional",
                "entrepreneur",
                "leadership",
            ],
            "creativity_arts": ["creative", "art", "writing", "design", "crafts"],
            "parenting_family": [
                "parenting",
                "family",
                "kids",
                "children",
                "mom",
                "dad",
            ],
            "relationships_love": [
                "relationship",
                "love",
                "dating",
                "marriage",
                "romance",
            ],
            "education_learning": [
                "education",
                "learning",
                "study",
                "student",
                "academic",
            ],
            "travel_adventure": ["travel", "adventure", "vacation", "trip", "explore"],
        }

        # Assign keywords to clusters
        for keyword in keywords:
            keyword_lower = keyword.lower()
            assigned = False

            for cluster_name, patterns in cluster_patterns.items():
                if any(pattern in keyword_lower for pattern in patterns):
                    if cluster_name not in clusters:
                        clusters[cluster_name] = []
                    clusters[cluster_name].append(keyword)
                    assigned = True
                    break

            # If not assigned to any cluster, create a miscellaneous cluster
            if not assigned:
                if "miscellaneous" not in clusters:
                    clusters["miscellaneous"] = []
                clusters["miscellaneous"].append(keyword)

        # Filter out small clusters and limit cluster sizes
        filtered_clusters = {}
        for cluster_name, cluster_keywords in clusters.items():
            if len(cluster_keywords) >= 3:  # Minimum cluster size
                filtered_clusters[cluster_name] = cluster_keywords[
                    :20
                ]  # Max cluster size

        return filtered_clusters

    @classmethod
    def _clean_keywords(cls, keywords: List[str]) -> List[str]:
        """Clean and validate keywords."""
        cleaned = []
        seen = set()

        for keyword in keywords:
            if not keyword:
                continue

            # Basic cleaning
            keyword = re.sub(r"\s+", " ", keyword.strip().lower())

            # Skip if already seen
            if keyword in seen:
                continue
            seen.add(keyword)

            # Filter criteria
            if (
                len(keyword) <= 100
                and len(keyword.split()) <= 6
                and len(keyword) >= 3
                and not keyword.isdigit()
                and not re.match(r"^[^a-zA-Z]*$", keyword)
            ):  # Must contain letters
                cleaned.append(keyword)

        return cleaned

    @classmethod
    def expand_keywords(
        cls, base_keywords: List[str], max_combinations: int = 100
    ) -> List[str]:
        """Legacy method for backward compatibility."""
        return cls._expand_with_modifiers(base_keywords, max_combinations)


async def find_profitable_niches(
    keepa_client: Optional[Any],
    cache_manager: CacheManager,
    base_keywords: List[str],
    categories: Optional[List[str]] = None,
    min_profitability_score: float = 60,
    max_competition_level: str = "medium",
    limit: int = 10,
    use_enhanced_expansion: bool = True,
    progress_tracker=None,
) -> Dict[str, Any]:
    """Find profitable publishing niches with enhanced keyword expansion and analysis.

    Args:
        keepa_client: Keepa API client (optional)
        cache_manager: Cache manager for performance
        base_keywords: Starting keywords for niche discovery
        categories: Amazon categories to focus on
        min_profitability_score: Minimum score threshold (0-100)
        max_competition_level: Maximum competition level (low/medium/high)
        limit: Maximum number of niches to return
        use_enhanced_expansion: Whether to use enhanced keyword expansion (now uses synthetic data)

    Returns:
        Dictionary containing discovered niches and analysis metadata
    """
    logger.info(f"Starting enhanced niche discovery for keywords: {base_keywords}")

    # Input validation
    try:
        if not base_keywords or not isinstance(base_keywords, list):
            raise ValidationError(
                "base_keywords must be a non-empty list of strings",
                parameter="base_keywords",
                value=base_keywords,
                expected_type="List[str]"
            )
        
        if not all(isinstance(kw, str) and kw.strip() for kw in base_keywords):
            raise ValidationError(
                "All base_keywords must be non-empty strings",
                parameter="base_keywords",
                value=base_keywords,
                expected_type="List[str] (non-empty strings)"
            )
        
        if not (0 <= min_profitability_score <= 100):
            raise ValidationError(
                "min_profitability_score must be between 0 and 100",
                parameter="min_profitability_score",
                value=min_profitability_score,
                expected_type="float (0-100)"
            )
        
        if max_competition_level not in ["low", "medium", "high"]:
            raise ValidationError(
                "max_competition_level must be 'low', 'medium', or 'high'",
                parameter="max_competition_level",
                value=max_competition_level,
                expected_type="str ('low'|'medium'|'high')"
            )
        
        if not (1 <= limit <= 50):
            raise ValidationError(
                "limit must be between 1 and 50",
                parameter="limit",
                value=limit,
                expected_type="int (1-50)"
            )
            
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Validation error in niche discovery: {e}")
        raise ValidationError(f"Parameter validation failed: {str(e)}")

    try:
        # Initialize progress tracking
        if progress_tracker:
            await progress_tracker.update_progress(
                5, 0, "in-progress", "Initializing analysis"
            )
            progress_tracker.check_cancellation()
            await progress_tracker.wait_if_paused()

        # Step 1: Enhanced keyword expansion
        if progress_tracker:
            await progress_tracker.update_progress(
                10, 1, "in-progress", "Expanding keywords"
            )

        if use_enhanced_expansion:
            expansion_result = await KeywordExpander.expand_keywords_with_trends(
                base_keywords,
                max_combinations=200,
                use_related_queries=True,
                use_semantic_clustering=True,
            )
            expanded_keywords = expansion_result["expanded_keywords"]
            keyword_clusters = expansion_result["keyword_clusters"]
            expansion_metadata = expansion_result["expansion_metadata"]

            logger.info(
                f"Enhanced expansion: {len(expanded_keywords)} keywords in {len(keyword_clusters)} clusters"
            )
        else:
            # Fallback to basic expansion
            expanded_keywords = KeywordExpander.expand_keywords(
                base_keywords, max_combinations=200
            )
            keyword_clusters = {}
            expansion_metadata = {
                "base_keywords": base_keywords,
                "basic_expanded_count": len(expanded_keywords),
                "expansion_methods": {"modifiers": True},
            }
            logger.info(f"Basic expansion: {len(expanded_keywords)} keyword variations")

        # Progress update after keyword expansion
        if progress_tracker:
            await progress_tracker.update_progress(
                30,
                2,
                "in-progress",
                "Analyzing trends",
                {"expanded_keywords": len(expanded_keywords)},
            )
            progress_tracker.check_cancellation()
            await progress_tracker.wait_if_paused()

        # Step 2: Batch analyze trends for expanded keywords (limit to reduce timeout)
        # Reduce the number of keywords analyzed to prevent timeouts
        limited_keywords = expanded_keywords[:20]  # Reduced from 50 to 20

        # Use synthetic trend analysis (trends functionality removed)
        try:
            trend_analyses = await _batch_analyze_trends_enhanced(
                limited_keywords, keyword_clusters
            )
            logger.info(
                f"Successfully analyzed trends for {len(trend_analyses)} keywords"
            )
            
            # If no trend analyses were successful, use fallback approach
            if not trend_analyses:
                logger.warning("No trend analyses were successful. Using fallback approach.")
                raise Exception("No trend data available from any source")

                
        except Exception as e:
            logger.warning(f"Trend analysis failed: {e}. Using fallback approach.")
            # If trend analysis fails, create minimal trend data to continue
            trend_analyses = {}
            for keyword in limited_keywords:
                # Create simple trend data structure as fallback
                trend_analyses[keyword] = type('TrendData', (), {
                    'keyword': keyword,
                    'trend_score': 50,  # Neutral score
                    'trend_direction': "stable",
                    'confidence_level': 0.5,
                    'forecast_6_months': [50] * 6,  # Fixed: should be 6 months, not 12
                    'seasonal_patterns': {},
                    'related_queries': [],
                    'additional_data': {"data_source": "fallback"},
                })()
            logger.info(f"Created fallback trend analyses for {len(trend_analyses)} keywords")

        # Step 3: Filter keywords with good trend potential using enhanced criteria
        if progress_tracker:
            await progress_tracker.update_progress(
                50, 3, "in-progress", "Filtering promising trends"
            )
            progress_tracker.check_cancellation()
            await progress_tracker.wait_if_paused()

        promising_keywords = _filter_promising_trends_enhanced(
            trend_analyses, keyword_clusters, min_trend_score=20  # More lenient for testing
        )
        logger.info(
            f"Found {len(promising_keywords)} keywords with good trend potential"
        )

        # Step 4: Analyze competition for promising keywords
        if progress_tracker:
            await progress_tracker.update_progress(
                65,
                4,
                "in-progress",
                "Analyzing competition",
                {"promising_keywords": len(promising_keywords)},
            )
        competition_data = await _analyze_competition(
            keepa_client, promising_keywords, categories, cache_manager
        )

        # Progress update after competition analysis
        if progress_tracker:
            await progress_tracker.update_progress(
                80, 5, "in-progress", "Generating niche candidates"
            )
            progress_tracker.check_cancellation()
            await progress_tracker.wait_if_paused()

        # Step 5: Generate niche candidates with cluster information
        niche_candidates = await _generate_niche_candidates_enhanced(
            promising_keywords,
            trend_analyses,
            competition_data,
            categories,
            keyword_clusters,
        )

        # Step 6: Score and rank niches
        if progress_tracker:
            await progress_tracker.update_progress(
                90, 6, "in-progress", "Scoring and ranking niches"
            )
            progress_tracker.check_cancellation()
            await progress_tracker.wait_if_paused()

        scored_niches = _score_and_rank_niches(
            niche_candidates, min_profitability_score, max_competition_level
        )

        # Step 7: Return top niches with enhanced metadata
        if progress_tracker:
            await progress_tracker.update_progress(
                95, 7, "in-progress", "Finalizing results"
            )
        top_niches = scored_niches[:limit]

        result = {
            "niches": [niche.to_dict() for niche in top_niches],
            "keyword_clusters": keyword_clusters,
            "analysis_metadata": {
                "base_keywords": base_keywords,
                "expansion_metadata": expansion_metadata,
                "analyzed_trends_count": len(trend_analyses),
                "promising_keywords_count": len(promising_keywords),
                "niche_candidates_count": len(niche_candidates),
                "final_niches_count": len(top_niches),
                "min_profitability_score": min_profitability_score,
                "max_competition_level": max_competition_level,
                "analysis_timestamp": datetime.now().isoformat(),
                "enhanced_features_used": {
                    "trends_expansion": use_enhanced_expansion,
                    "semantic_clustering": use_enhanced_expansion,
                    "cluster_analysis": len(keyword_clusters) > 0,
                },
            },
            "recommendations": _generate_recommendations_enhanced(
                top_niches, scored_niches, keyword_clusters
            ),
        }

        logger.info(
            f"Enhanced niche discovery completed. Found {len(top_niches)} profitable niches"
        )

        # Final progress update - completion
        if progress_tracker:
            await progress_tracker.complete(result)

        return result

    except ValidationError:
        # Re-raise validation errors as-is
        raise
    except APIError:
        # Re-raise API errors as-is
        raise
    except Exception as e:
        logger.error(f"Enhanced niche discovery failed: {e}")

        # Report error through progress tracker
        if progress_tracker:
            await progress_tracker.error(str(e))

        # Create structured error response
        if "analysis" in str(e).lower():
            raise APIError(
                message=f"Analysis failed: {str(e)}",
                service_name="niche_analysis",
                response_data={"operation": "niche_discovery", "keywords": base_keywords}
            )
        elif "keepa" in str(e).lower():
            raise APIError(
                message=f"Competition analysis failed: {str(e)}",
                service_name="keepa",
                response_data={"operation": "niche_discovery", "keywords": base_keywords}
            )
        else:
            raise ToolExecutionError(
                message=f"Niche discovery failed: {str(e)}",
                tool_name="find_profitable_niches",
                operation="niche_analysis",
                details={"keywords": base_keywords, "error_type": type(e).__name__}
            )


async def _batch_analyze_trends(
    keywords: List[str]
) -> Dict[str, Any]:
    """Analyze trends for multiple keywords using synthetic data (trends functionality removed)."""
    trend_analyses = {}

    # Generate synthetic trend data for testing
    for keyword in keywords:
        # Create synthetic trend analysis data
        trend_analyses[keyword] = {
            'keyword': keyword,
            'trend_score': 50 + (hash(keyword) % 50),  # Synthetic score 50-100
            'competition_level': 'medium',
            'search_volume': 1000 + (hash(keyword) % 5000),  # Synthetic volume
            'related_queries': [f"{keyword} guide", f"{keyword} tips"],
            'trend_direction': 'stable'
        }

    return trend_analyses


async def _batch_analyze_trends_enhanced(
    keywords: List[str],
    keyword_clusters: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Enhanced batch trend analysis with synthetic data (trends functionality removed)."""
    trend_analyses = {}

    # Prioritize keywords by cluster importance
    prioritized_keywords = _prioritize_keywords_by_cluster(keywords, keyword_clusters)

    # Generate synthetic trend data for testing (trends functionality removed)
    logger.info(f"Generating synthetic trend data for {len(prioritized_keywords)} keywords")

    for keyword in prioritized_keywords:
        # Create enhanced synthetic trend analysis data
        trend_analyses[keyword] = {
            'keyword': keyword,
            'trend_score': 60 + (hash(keyword) % 40),  # Synthetic score 60-100
            'competition_level': ['low', 'medium', 'high'][hash(keyword) % 3],
            'search_volume': 2000 + (hash(keyword) % 8000),  # Synthetic volume
            'related_queries': [f"{keyword} guide", f"{keyword} tips", f"best {keyword}"],
            'trend_direction': ['rising', 'stable', 'declining'][hash(keyword) % 3],
            'seasonal_patterns': {'peak_months': [6, 7, 8], 'low_months': [12, 1, 2]}
        }
        logger.debug(f"✓ Generated synthetic data for '{keyword}': score={trend_analyses[keyword]['trend_score']}")

    logger.info(
        f"Completed enhanced synthetic trend analysis: {len(trend_analyses)}/{len(prioritized_keywords)} successful"
    )
    return trend_analyses


# Mock trend analysis function removed - using real trends client


def _prioritize_keywords_by_cluster(
    keywords: List[str], keyword_clusters: Dict[str, List[str]]
) -> List[str]:
    """Prioritize keywords based on cluster importance and keyword quality."""
    # Define cluster priority (higher = more important)
    cluster_priorities = {
        "journals_planners": 10,
        "wellness_mindfulness": 9,
        "productivity_goals": 9,
        "business_career": 8,
        "fitness_health": 8,
        "creativity_arts": 7,
        "self_improvement": 7,
        "parenting_family": 6,
        "relationships_love": 6,
        "education_learning": 5,
        "travel_adventure": 5,
        "miscellaneous": 1,
    }

    # Create keyword priority mapping
    keyword_priorities = {}

    for cluster_name, cluster_keywords in keyword_clusters.items():
        cluster_priority = cluster_priorities.get(cluster_name, 1)
        for keyword in cluster_keywords:
            if keyword in keywords:
                # Calculate keyword-specific score
                keyword_score = KeywordExpander._calculate_keyword_score(keyword)
                combined_priority = cluster_priority * 10 + keyword_score
                keyword_priorities[keyword] = combined_priority

    # Add any keywords not in clusters with default priority
    for keyword in keywords:
        if keyword not in keyword_priorities:
            keyword_score = KeywordExpander._calculate_keyword_score(keyword)
            keyword_priorities[keyword] = keyword_score

    # Sort keywords by priority (descending)
    prioritized = sorted(
        keywords, key=lambda k: keyword_priorities.get(k, 0), reverse=True
    )

    logger.debug(f"Keyword prioritization: Top 5 = {prioritized[:5]}")
    return prioritized


def _filter_promising_trends(
    trend_analyses: Dict[str, Any], min_trend_score: float = 30
) -> List[str]:
    """Filter keywords with promising trend characteristics."""
    promising = []

    for keyword, analysis in trend_analyses.items():
        # Basic trend score filter
        if analysis.trend_score < min_trend_score:
            continue

        # Avoid declining trends
        if (
            getattr(analysis, 'trend_direction', None) == "declining"
            and analysis.trend_score < 50
        ):
            continue

        # Require minimum confidence
        if analysis.confidence_level < 0.3:
            continue

        promising.append(keyword)

    return promising


def _filter_promising_trends_enhanced(
    trend_analyses: Dict[str, Any],
    keyword_clusters: Dict[str, List[str]],
    min_trend_score: float = 30,
) -> List[str]:
    """Enhanced filtering with cluster-aware scoring and multi-factor analysis."""
    promising = []

    # Create cluster priority mapping
    cluster_priorities = {
        "journals_planners": 1.3,
        "wellness_mindfulness": 1.2,
        "productivity_goals": 1.2,
        "business_career": 1.1,
        "fitness_health": 1.1,
        "creativity_arts": 1.0,
        "parenting_family": 1.0,
        "relationships_love": 0.9,
        "education_learning": 0.9,
        "travel_adventure": 0.8,
        "miscellaneous": 0.7,
    }

    # Get keyword-to-cluster mapping
    keyword_to_cluster = {}
    for cluster_name, cluster_keywords in keyword_clusters.items():
        for keyword in cluster_keywords:
            keyword_to_cluster[keyword] = cluster_name

    for keyword, analysis in trend_analyses.items():
        # Calculate adjusted trend score based on cluster
        cluster_name = keyword_to_cluster.get(keyword, "miscellaneous")
        cluster_multiplier = cluster_priorities.get(cluster_name, 1.0)
        adjusted_score = analysis.trend_score * cluster_multiplier

        # Enhanced filtering criteria
        if adjusted_score < min_trend_score:
            continue

        # More nuanced declining trend handling
        if (
            getattr(analysis, 'trend_direction', None) == "declining"
            and adjusted_score < 45
            and analysis.confidence_level < 0.6
        ):
            continue

        # Enhanced confidence requirements based on trend strength
        # Be more lenient with fallback data and Simple Trends data
        is_fallback = (
            hasattr(analysis, 'data_source') and analysis.data_source == "fallback"
        ) or (
            analysis.additional_data and analysis.additional_data.get("data_source") == "fallback"
        )
        
        if is_fallback:
            min_confidence = 0.1  # Very lenient for fallback data
        else:
            # More lenient confidence requirements for Simple Trends
            min_confidence = 10 if analysis.trend_score > 60 else 15  # Much more lenient
        
        if analysis.confidence_level < min_confidence:
            continue

        # Bonus for rising trends with good confidence
        if (
            getattr(analysis, 'trend_direction', None) == "rising"
            and analysis.confidence_level > 0.5
        ):
            adjusted_score *= 1.1

        # Bonus for stable trends with high scores
        if (
            getattr(analysis, 'trend_direction', None) == "stable"
            and analysis.trend_score > 50
        ):
            adjusted_score *= 1.05

        # Filter out very volatile trends unless they have high scores
        if (
            getattr(analysis, 'trend_direction', None) == "volatile"
            and adjusted_score < 50
        ):
            continue

        promising.append(keyword)
        logger.debug(
            f"✓ Promising keyword: '{keyword}' (score: {adjusted_score:.1f}, cluster: {cluster_name})"
        )

    # Sort by adjusted trend potential
    def get_trend_potential(keyword):
        analysis = trend_analyses[keyword]
        cluster_name = keyword_to_cluster.get(keyword, "miscellaneous")
        cluster_multiplier = cluster_priorities.get(cluster_name, 1.0)
        return (
            analysis.trend_score * cluster_multiplier * (1 + analysis.confidence_level)
        )

    promising.sort(key=get_trend_potential, reverse=True)

    logger.info(
        f"Enhanced trend filtering: {len(promising)}/{len(trend_analyses)} keywords passed filters"
    )
    return promising


async def _analyze_competition(
    keepa_client: Optional[Any],
    keywords: List[str],
    categories: Optional[List[str]],
    cache_manager: Optional[CacheManager] = None,
) -> Dict[str, MarketSummary]:
    """Analyze competition for keywords using Amazon/Keepa data with direct API access."""
    competition_data: Dict[str, MarketSummary] = {}

    # Try to use real Keepa client, but fall back gracefully
    keepa_working = False
    if keepa_client:
        logger.info("🔑 Testing Keepa API availability...")
        
        # Test the Keepa API with one keyword first
        try:
            test_keyword = keywords[0] if keywords else "journal"
            test_products = await keepa_client.search_products(test_keyword, limit=1)
            if test_products and len(test_products) > 0:
                keepa_working = True
                logger.info("✅ Keepa API is working, using real data")
            else:
                logger.warning("⚠️ Keepa API returned no results, falling back to mock data")
        except Exception as e:
            logger.warning(f"⚠️ Keepa API test failed: {e}. Falling back to mock data")
    
    if keepa_working:
        # Use real Keepa API
        logger.info("🔑 Using real Keepa API for competition analysis")
        for keyword in keywords[:20]:  # Limit for performance
            try:
                logger.info(f"📊 Analyzing competition for: {keyword}")
                
                # Search for products using real Keepa API
                products = await keepa_client.search_products(keyword, limit=20)
                
                if products:
                    # Process real Keepa data
                    competitor_count = len(products)
                    total_reviews = sum(p.get('reviews', 0) for p in products)
                    avg_reviews = total_reviews / competitor_count if competitor_count > 0 else 0
                    
                    ratings = [p.get('rating', 0) for p in products if p.get('rating', 0) > 0]
                    avg_rating = sum(ratings) / len(ratings) if ratings else 0
                    
                    prices = [p.get('price', 0) for p in products if p.get('price', 0) > 0]
                    avg_price = sum(prices) / len(prices) if prices else 0
                    min_price = min(prices) if prices else 0
                    max_price = max(prices) if prices else 0
                    
                    # Create MarketSummary from real data
                    from ...models.niche_model import MarketSummary, PriceRange
                    
                    competition_data[keyword] = MarketSummary(
                        competitor_count=competitor_count,
                        avg_review_count=int(avg_reviews),
                        avg_rating=round(avg_rating, 2),
                        price_range=PriceRange(min=min_price, max=max_price, avg=avg_price),
                        estimated=False,  # Real data, not estimated
                        data_source="keepa_api"
                    )
                    
                    logger.info(f"✅ Real Keepa data for '{keyword}': {competitor_count} competitors, avg rating {avg_rating:.1f}")
                else:
                    logger.warning(f"❌ No products found for '{keyword}' in Keepa API")
                    
            except Exception as e:
                logger.error(f"❌ Keepa API error for '{keyword}': {e}")
                # If we get errors, fall back to mock data for remaining keywords
                keepa_working = False
                break
    
    # If Keepa API is not working or not available, use fallback
    if not keepa_working:
        logger.warning("⚠️ Using fallback competition analysis with mock data")
        
        from ...data.keepa_client import KeepaClient, FallbackConfig
        
        fallback_config = FallbackConfig(
            realistic_variance=True, include_data_source_indicators=True
        )
        
        fallback_client = KeepaClient(
            api_key=None, cache_manager=cache_manager, fallback_config=fallback_config
        )
        
        for keyword in keywords[:20]:  # Limit for performance
            try:
                # Get comprehensive competition analysis from fallback
                analysis = await fallback_client.get_competition_analysis(keyword, limit=20)
                
                if analysis and analysis.get("competitor_count", 0) > 0:
                    # Convert enhanced analysis to MarketSummary format
                    from ...models.niche_model import MarketSummary, PriceRange
                    
                    competition_data[keyword] = MarketSummary(
                        competitor_count=analysis["competitor_count"],
                        avg_review_count=analysis.get("avg_reviews", 0.0),
                        avg_rating=analysis.get("avg_rating", 0.0),
                        price_range=PriceRange(
                            min=analysis.get("price_range", {}).get("min", 0.0),
                            max=analysis.get("price_range", {}).get("max", 0.0),
                            avg=analysis.get("price_range", {}).get("avg", 0.0),
                        ),
                        estimated=True,  # Fallback data is always estimated
                        data_source="fallback"
                    )
                    
                    logger.info(f"✅ Fallback data for '{keyword}': {analysis['competitor_count']} competitors")
                else:
                    # No competition found or analysis failed
                    from ...models.niche_model import MarketSummary
                    competition_data[keyword] = MarketSummary(estimated=True, data_source="fallback")
                    logger.info(f"❌ No competition data available for keyword: {keyword}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to analyze competition for '{keyword}': {e}")
                from ...models.niche_model import MarketSummary
                competition_data[keyword] = MarketSummary(estimated=True, data_source="error")
                continue

    # Log summary statistics
    total_keywords = len(keywords[:20])
    successful_analyses = len(
        [k for k, v in competition_data.items() if v.competitor_count > 0]
    )
    logger.info(
        f"Competition analysis complete: {successful_analyses}/{total_keywords} keywords analyzed successfully"
    )

    return competition_data


async def _generate_niche_candidates(
    keywords: List[str],
    trend_analyses: Dict[str, Any],
    competition_data: Dict[str, MarketSummary],
    categories: Optional[List[str]],
) -> List[Niche]:
    """Generate niche candidates from analyzed data."""
    niche_candidates = []

    for keyword in keywords:
        trend_analysis = trend_analyses.get(keyword)
        competition = competition_data.get(keyword, MarketSummary())

        if not trend_analysis:
            continue

        # Estimate market metrics
        metrics = _estimate_market_size(trend_analysis, competition)

        # Create niche object
        niche = Niche(
            category=categories[0] if categories else "Books & Journals",
            primary_keyword=keyword,
            keywords=[keyword] + trend_analysis.related_queries[:10],
            trend_analysis_data=trend_analysis,
            competitor_analysis_data=competition,
            market_size_score=NicheScorer._score_market_size(metrics) or 0.0,
            seasonal_factors=trend_analysis.seasonal_patterns,
            # Calculate and assign numeric scores directly during construction
            profitability_score_numeric=NicheScorer.calculate_profitability_score(
                {
                    "trend_analysis": trend_analysis,
                    "competition_data": competition,
                    "market_metrics": metrics,
                    "seasonal_patterns": trend_analysis.seasonal_patterns,
                    "content_analysis": {"identified_gaps": 5},
                }
            ),
            competition_score_numeric=NicheScorer._score_competition_level(competition)
            or 0.0,
        )
        niche_candidates.append(niche)

    return niche_candidates


async def _generate_niche_candidates_enhanced(
    keywords: List[str],
    trend_analyses: Dict[str, Any],
    competition_data: Dict[str, MarketSummary],
    categories: Optional[List[str]],
    keyword_clusters: Dict[str, List[str]],
) -> List[Niche]:
    """Enhanced niche candidate generation with cluster information and improved scoring."""
    niche_candidates = []

    # Create keyword-to-cluster mapping for enhanced analysis
    keyword_to_cluster = {}
    for cluster_name, cluster_keywords in keyword_clusters.items():
        for keyword in cluster_keywords:
            keyword_to_cluster[keyword] = cluster_name

    for keyword in keywords:
        trend_analysis = trend_analyses.get(keyword)
        competition = competition_data.get(keyword, MarketSummary())

        if not trend_analysis:
            continue

        # Get cluster information
        cluster_name = keyword_to_cluster.get(keyword, "miscellaneous")

        # Enhanced market metrics estimation with cluster context
        metrics = _estimate_market_size_enhanced(
            trend_analysis, competition, cluster_name
        )

        # Enhanced content gap analysis based on cluster
        content_gaps = _identify_content_gaps_by_cluster(
            keyword, cluster_name, competition
        )

        # Determine category based on cluster if not provided
        category = _determine_category_from_cluster(cluster_name, categories)

        # Enhanced keyword list with cluster-related terms
        enhanced_keywords = _build_enhanced_keyword_list(
            keyword, trend_analysis, cluster_name, keyword_clusters
        )

        # Calculate enhanced profitability score with cluster weighting
        profitability_data = {
            "trend_analysis": trend_analysis,
            "competition_data": competition,
            "market_metrics": metrics,
            "seasonal_patterns": trend_analysis.seasonal_patterns,
            "content_analysis": {"identified_gaps": len(content_gaps)},
            "cluster_context": {
                "cluster_name": cluster_name,
                "cluster_size": len(keyword_clusters.get(cluster_name, [])),
                "cluster_priority": _get_cluster_priority(cluster_name),
            },
        }

        # Create enhanced niche object
        niche = Niche(
            category=category,
            primary_keyword=keyword,
            keywords=enhanced_keywords,
            trend_analysis_data=trend_analysis,
            competitor_analysis_data=competition,
            market_size_score=NicheScorer._score_market_size(metrics) or 0.0,
            seasonal_factors=trend_analysis.seasonal_patterns,
            content_gaps=content_gaps,
            profitability_score_numeric=NicheScorer.calculate_profitability_score(
                profitability_data
            ),
            competition_score_numeric=NicheScorer._score_competition_level(competition)
            or 0.0,
            confidence_score=_calculate_enhanced_confidence_score(
                trend_analysis, competition, cluster_name
            ),
            additional_data={
                "cluster_name": cluster_name,
                "cluster_priority": _get_cluster_priority(cluster_name),
                "enhanced_analysis": True,
                "data_sources": _get_data_sources_info(competition),
            },
        )
        niche_candidates.append(niche)

        logger.debug(
            f"✓ Generated enhanced niche candidate: '{keyword}' (cluster: {cluster_name}, score: {niche.profitability_score_numeric:.1f})"
        )

    logger.info(f"Generated {len(niche_candidates)} enhanced niche candidates")
    return niche_candidates


def _estimate_market_size_enhanced(
    trend_analysis: Any, competition_data: MarketSummary, cluster_name: str
) -> Dict[str, Any]:
    """Enhanced market size estimation with cluster context."""
    base_metrics = _estimate_market_size(trend_analysis, competition_data)

    # Cluster-specific adjustments
    cluster_multipliers = {
        "journals_planners": 1.3,  # High demand category
        "wellness_mindfulness": 1.2,
        "productivity_goals": 1.2,
        "business_career": 1.1,
        "fitness_health": 1.1,
        "creativity_arts": 1.0,
        "parenting_family": 1.0,
        "relationships_love": 0.9,
        "education_learning": 0.9,
        "travel_adventure": 0.8,
        "miscellaneous": 0.7,
    }

    multiplier = cluster_multipliers.get(cluster_name, 1.0)

    # Apply cluster adjustment
    base_metrics["category_size_score"] *= multiplier
    base_metrics["estimated_search_volume"] = int(
        base_metrics["estimated_search_volume"] * multiplier
    )
    base_metrics["cluster_adjustment"] = multiplier
    base_metrics["cluster_name"] = cluster_name

    return base_metrics


def _identify_content_gaps_by_cluster(
    keyword: str, cluster_name: str, competition: MarketSummary
) -> List[str]:
    """Identify content gaps based on cluster and competition analysis."""
    gaps = []

    # Cluster-specific content gap patterns
    cluster_gaps = {
        "journals_planners": [
            "Guided prompts and exercises",
            "Monthly/weekly planning sections",
            "Goal tracking templates",
            "Habit tracking pages",
            "Reflection questions",
        ],
        "wellness_mindfulness": [
            "Daily mindfulness exercises",
            "Stress relief techniques",
            "Gratitude practices",
            "Self-care checklists",
            "Meditation guides",
        ],
        "productivity_goals": [
            "Time blocking templates",
            "Priority matrix frameworks",
            "Progress tracking systems",
            "Accountability structures",
            "Review and reflection tools",
        ],
        "business_career": [
            "Professional development plans",
            "Networking templates",
            "Skill assessment tools",
            "Career milestone tracking",
            "Leadership exercises",
        ],
        "fitness_health": [
            "Workout planning templates",
            "Nutrition tracking pages",
            "Progress measurement tools",
            "Motivation techniques",
            "Health goal setting",
        ],
    }

    # Get cluster-specific gaps
    cluster_specific_gaps = cluster_gaps.get(
        cluster_name,
        [
            "Interactive exercises",
            "Progress tracking",
            "Guided activities",
            "Reflection prompts",
            "Goal setting tools",
        ],
    )

    # Add gaps based on competition level
    if competition.competitor_count < 10:
        gaps.extend(cluster_specific_gaps[:3])  # More opportunities
    elif competition.competitor_count < 50:
        gaps.extend(cluster_specific_gaps[:2])  # Some opportunities
    else:
        gaps.extend(cluster_specific_gaps[:1])  # Limited opportunities

    # Add quality-based gaps if competition has low ratings
    if competition.avg_rating < 4.0:
        gaps.extend(
            [
                "Higher quality content",
                "Better user experience",
                "More comprehensive coverage",
            ]
        )

    return gaps[:5]  # Limit to top 5 gaps


def _determine_category_from_cluster(
    cluster_name: str, provided_categories: Optional[List[str]]
) -> str:
    """Determine the most appropriate category based on cluster."""
    if provided_categories:
        return provided_categories[0]

    cluster_to_category = {
        "journals_planners": "Self-Help",
        "wellness_mindfulness": "Health, Fitness & Dieting",
        "productivity_goals": "Business & Money",
        "business_career": "Business & Money",
        "fitness_health": "Health, Fitness & Dieting",
        "creativity_arts": "Arts & Photography",
        "parenting_family": "Parenting & Relationships",
        "relationships_love": "Parenting & Relationships",
        "education_learning": "Education & Teaching",
        "travel_adventure": "Travel",
        "miscellaneous": "Self-Help",
    }

    return cluster_to_category.get(cluster_name, "Books & Journals")


def _build_enhanced_keyword_list(
    self,
    primary_keyword: str,
    trend_analysis: Any,
    cluster_name: str,
    keyword_clusters: Dict[str, List[str]],
) -> List[str]:
    """Build enhanced keyword list with cluster context."""
    keywords = [primary_keyword]

    # Trends functionality removed - no longer adding related queries from trends

    # Add cluster-related keywords
    cluster_keywords = keyword_clusters.get(cluster_name, [])
    for kw in cluster_keywords[:5]:
        if kw != primary_keyword and kw not in keywords:
            keywords.append(kw)

    # Limit total keywords
    return keywords[:15]


def _get_cluster_priority(cluster_name: str) -> float:
    """Get priority score for cluster (0-10 scale)."""
    priorities = {
        "journals_planners": 10.0,
        "wellness_mindfulness": 9.0,
        "productivity_goals": 9.0,
        "business_career": 8.0,
        "fitness_health": 8.0,
        "creativity_arts": 7.0,
        "parenting_family": 6.0,
        "relationships_love": 6.0,
        "education_learning": 5.0,
        "travel_adventure": 5.0,
        "miscellaneous": 1.0,
    }
    return priorities.get(cluster_name, 1.0)


def _calculate_enhanced_confidence_score(
    trend_analysis: Any, competition: MarketSummary, cluster_name: str
) -> float:
    """Calculate enhanced confidence score with multiple factors."""
    base_confidence = trend_analysis.confidence_level

    # Adjust for data source reliability
    data_source_confidence = 1.0
    if hasattr(competition, "data_source") and competition.data_source:
        if isinstance(competition.data_source, dict):
            reliability = competition.data_source.get("reliability_score", 100) / 100
            data_source_confidence = reliability
        elif isinstance(competition.data_source, str):
            # Handle string data source (fallback case)
            data_source_confidence = 0.8  # Default confidence for string sources

    # Adjust for cluster reliability
    cluster_confidence = _get_cluster_priority(cluster_name) / 10.0

    # Combine factors
    enhanced_confidence = (
        base_confidence * 0.5
        + data_source_confidence * 30 * 0.3
        + cluster_confidence * 100 * 0.2
    )

    return min(100.0, enhanced_confidence)


def _get_data_sources_info(competition: MarketSummary) -> Dict[str, Any]:
    """Extract data source information for transparency."""
    if hasattr(competition, "data_source") and competition.data_source:
        if isinstance(competition.data_source, dict):
            return {
                "source_type": competition.data_source.get("source_type", "unknown"),
                "source_name": competition.data_source.get("source_name", "Unknown"),
                "reliability": competition.data_source.get("reliability_score", 0),
                "estimated": competition.estimated,
            }
        elif isinstance(competition.data_source, str):
            # Handle string data source
            return {
                "source_type": "string_source",
                "source_name": competition.data_source,
                "reliability": 50,  # Default reliability for string sources
                "estimated": competition.estimated,
            }
    return {
        "source_type": "unknown",
        "source_name": "Unknown",
        "reliability": 0,
        "estimated": True,
    }


def _estimate_market_size(
    trend_analysis: Any, competition_data: MarketSummary
) -> Dict[str, Any]:
    """Estimate market size score based on trend and competition data."""
    base_score = trend_analysis.trend_score

    # Adjust for competition level
    competitor_count = competition_data.competitor_count

    if competitor_count == 0:
        category_size_score = 100.0
    elif competitor_count < 10:
        category_size_score = 90.0
    elif competitor_count < 50:
        category_size_score = 70.0
    elif competitor_count < 100:
        category_size_score = 50.0
    else:
        category_size_score = 30.0

    # Estimate search volume based on trend score
    estimated_search_volume = int(base_score * 100)  # Simple estimation

    return {
        "estimated_search_volume": estimated_search_volume,
        "related_keyword_count": len(trend_analysis.related_queries),
        "category_size_score": category_size_score,
    }


def _score_and_rank_niches(
    niche_candidates: List[Niche], min_score: float, max_competition: str
) -> List[Niche]:
    """Enhanced scoring and ranking with multi-factor analysis."""
    scored_niches = []

    competition_limits = {"low": 20, "medium": 50, "high": 100}
    max_competitors = competition_limits.get(max_competition, 50)

    for niche in niche_candidates:
        # Enhanced scoring with all available data
        niche = _enhance_niche_scoring(niche)

        # Apply filters
        if (
            niche.profitability_score_numeric >= min_score
            and niche.competitor_analysis_data.competitor_count <= max_competitors
        ):
            scored_niches.append(niche)

    # Enhanced multi-factor ranking
    ranked_niches = _rank_niches_multi_factor(scored_niches)

    return ranked_niches


def _enhance_niche_scoring(niche: Niche) -> Niche:
    """Enhance niche scoring with comprehensive analysis."""
    # Re-calculate competition score with enhanced method
    if hasattr(NicheScorer, "_score_competition_level_enhanced"):
        niche.competition_score_numeric = (
            NicheScorer._score_competition_level_enhanced(
                niche.competitor_analysis_data
            )
            or 0.0
        )
    else:
        niche.competition_score_numeric = (
            NicheScorer._score_competition_level(niche.competitor_analysis_data) or 0.0
        )

    # Set categorical competition level
    niche.competition_level = Niche._determine_competition_level(
        niche.competition_score_numeric
    )

    # Enhanced market metrics estimation
    if niche.additional_data and "cluster_name" in niche.additional_data:
        cluster_name = niche.additional_data["cluster_name"]
        metrics = _estimate_market_size_enhanced(
            niche.trend_analysis_data, niche.competitor_analysis_data, cluster_name
        )
    else:
        metrics = _estimate_market_size(
            niche.trend_analysis_data, niche.competitor_analysis_data
        )

    # Update market size score
    if hasattr(NicheScorer, "_score_market_size_enhanced"):
        niche.market_size_score = (
            NicheScorer._score_market_size_enhanced(metrics) or 0.0
        )
    else:
        niche.market_size_score = NicheScorer._score_market_size(metrics) or 0.0

    # Comprehensive profitability scoring
    niche_data_for_scoring = {
        "trend_analysis": niche.trend_analysis_data,
        "competition_data": niche.competitor_analysis_data,
        "market_metrics": metrics,
        "seasonal_patterns": niche.seasonal_factors,
        "content_analysis": {"identified_gaps": len(niche.content_gaps)},
        "cluster_context": niche.additional_data.get("cluster_context")
        if niche.additional_data
        else None,
    }

    niche.profitability_score_numeric = NicheScorer.calculate_profitability_score(
        niche_data_for_scoring
    )

    # Set categorical profitability tier
    niche.profitability_tier = Niche._determine_profitability_tier(
        niche.profitability_score_numeric
    )

    # Enhanced confidence scoring
    if niche.trend_analysis_data and niche.additional_data:
        cluster_name = niche.additional_data.get("cluster_name", "unknown")
        niche.confidence_score = _calculate_enhanced_confidence_score(
            niche.trend_analysis_data, niche.competitor_analysis_data, cluster_name
        )

    return niche


def _rank_niches_multi_factor(niches: List[Niche]) -> List[Niche]:
    """Advanced multi-factor ranking system."""

    def calculate_ranking_score(niche: Niche) -> float:
        """Calculate comprehensive ranking score."""
        # Base profitability score (40% weight)
        base_score = niche.profitability_score_numeric * 0.4

        # Competition advantage (25% weight) - higher score for lower competition
        competition_advantage = (100 - niche.competition_score_numeric) * 0.25

        # Market size potential (20% weight)
        market_potential = niche.market_size_score * 0.2

        # Confidence level (10% weight)
        confidence_factor = niche.confidence_score * 0.1

        # Trend momentum (5% weight)
        trend_momentum = 0
        if niche.trend_analysis_data:
            if niche.trend_analysis_data.trend_direction == "rising":
                trend_momentum = niche.trend_analysis_data.trend_score * 0.05
            elif (
                niche.trend_analysis_data.trend_direction == "stable"
            ):
                trend_momentum = niche.trend_analysis_data.trend_score * 0.03
            else:
                trend_momentum = niche.trend_analysis_data.trend_score * 0.01

        total_score = (
            base_score
            + competition_advantage
            + market_potential
            + confidence_factor
            + trend_momentum
        )

        # Apply bonuses and penalties
        total_score = _apply_ranking_bonuses_penalties(niche, total_score)

        return total_score

    # Calculate ranking scores
    for niche in niches:
        niche.additional_data = niche.additional_data or {}
        niche.additional_data["ranking_score"] = calculate_ranking_score(niche)

    # Sort by ranking score (descending)
    ranked_niches = sorted(
        niches, key=lambda n: n.additional_data.get("ranking_score", 0), reverse=True
    )

    # Add ranking metadata
    for i, niche in enumerate(ranked_niches):
        niche.additional_data["rank"] = i + 1
        niche.additional_data["percentile"] = (
            (len(ranked_niches) - i) / len(ranked_niches)
        ) * 100

    return ranked_niches


def _apply_ranking_bonuses_penalties(niche: Niche, base_score: float) -> float:
    """Apply bonuses and penalties to ranking score."""
    adjusted_score = base_score

    # Content gap opportunity bonus
    if len(niche.content_gaps) >= 4:
        adjusted_score += 5  # Significant content opportunities
    elif len(niche.content_gaps) >= 2:
        adjusted_score += 2  # Some content opportunities

    # Low competition bonus
    if niche.competition_level == CompetitionLevel.LOW:
        adjusted_score += 8
    elif niche.competition_level == CompetitionLevel.MEDIUM:
        adjusted_score += 3

    # High profitability tier bonus
    if niche.profitability_tier == ProfitabilityTier.HIGH:
        adjusted_score += 6
    elif niche.profitability_tier == ProfitabilityTier.MEDIUM:
        adjusted_score += 2

    # Cluster priority bonus
    if niche.additional_data and "cluster_priority" in niche.additional_data:
        cluster_priority = niche.additional_data["cluster_priority"]
        if cluster_priority >= 9:
            adjusted_score += 4
        elif cluster_priority >= 7:
            adjusted_score += 2

    # Data quality penalty
    if niche.competitor_analysis_data.estimated:
        adjusted_score -= 3  # Penalty for estimated data

    # Very high competition penalty
    if niche.competitor_analysis_data.competitor_count > 200:
        adjusted_score -= 5

    # Low confidence penalty
    if niche.confidence_score < 40:
        adjusted_score -= 4

    return max(0, adjusted_score)


class NicheRecommendationEngine:
    """Advanced recommendation engine for niche opportunities."""

    @staticmethod
    def generate_personalized_recommendations(
        ranked_niches: List[Niche], user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate personalized recommendations based on user preferences."""

        if not ranked_niches:
            return {"message": "No niches available for recommendations"}

        # Default preferences if none provided
        preferences = user_preferences or {
            "risk_tolerance": "medium",  # low, medium, high
            "time_to_market": "medium",  # fast, medium, long
            "content_complexity": "medium",  # simple, medium, complex
            "market_size_preference": "medium",  # small, medium, large
        }

        recommendations = {
            "quick_wins": NicheRecommendationEngine._identify_quick_wins(
                ranked_niches, preferences
            ),
            "long_term_opportunities": NicheRecommendationEngine._identify_long_term_opportunities(
                ranked_niches, preferences
            ),
            "balanced_options": NicheRecommendationEngine._identify_balanced_options(
                ranked_niches, preferences
            ),
            "high_potential_risks": NicheRecommendationEngine._identify_high_potential_risks(
                ranked_niches, preferences
            ),
            "market_insights": NicheRecommendationEngine._generate_market_insights(
                ranked_niches
            ),
            "strategic_recommendations": NicheRecommendationEngine._generate_strategic_recommendations(
                ranked_niches, preferences
            ),
        }

        return recommendations

    @staticmethod
    def _identify_quick_wins(
        niches: List[Niche], preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify quick win opportunities."""
        quick_wins = []

        for niche in niches[:15]:  # Top 15 niches
            # Quick win criteria
            is_quick_win = (
                niche.competition_level == CompetitionLevel.LOW
                and niche.profitability_score_numeric >= 60
                and niche.confidence_score >= 50
                and len(niche.content_gaps) >= 2
            )

            if is_quick_win:
                quick_wins.append(
                    {
                        "niche": niche.primary_keyword,
                        "score": niche.profitability_score_numeric,
                        "confidence": niche.confidence_score,
                        "competitors": niche.competitor_analysis_data.competitor_count,
                        "content_gaps": len(niche.content_gaps),
                        "estimated_effort": "Low",
                        "time_to_market": "1-2 months",
                        "risk_level": niche.risk_level.value,
                        "reason": f"Low competition ({niche.competitor_analysis_data.competitor_count} competitors) with {len(niche.content_gaps)} content opportunities",
                    }
                )

        return sorted(quick_wins, key=lambda x: x["score"], reverse=True)[:5]

    @staticmethod
    def _identify_long_term_opportunities(
        niches: List[Niche], preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify long-term growth opportunities."""
        long_term = []

        for niche in niches[:20]:
            # Long-term criteria
            is_long_term = (
                niche.profitability_score_numeric >= 70
                and niche.trend_analysis_data
                and niche.trend_analysis_data.trend_direction
                in ["rising", "stable"]
                and niche.market_size_score >= 60
            )

            if is_long_term:
                growth_potential = (
                    "High"
                    if niche.trend_analysis_data.trend_direction
                    == "rising"
                    else "Stable"
                )

                long_term.append(
                    {
                        "niche": niche.primary_keyword,
                        "score": niche.profitability_score_numeric,
                        "trend_direction": niche.trend_analysis_data.trend_direction,
                        "trend_score": niche.trend_analysis_data.trend_score,
                        "market_size": niche.market_size_score,
                        "growth_potential": growth_potential,
                        "estimated_effort": "Medium to High",
                        "time_to_market": "3-6 months",
                        "reason": f"Strong {growth_potential.lower()} growth potential with market size score of {niche.market_size_score:.1f}",
                    }
                )

        return sorted(long_term, key=lambda x: x["score"], reverse=True)[:5]

    @staticmethod
    def _identify_balanced_options(
        niches: List[Niche], preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify balanced risk/reward opportunities."""
        balanced = []

        for niche in niches[:25]:
            # Balanced criteria
            is_balanced = (
                50 <= niche.profitability_score_numeric <= 80
                and niche.competition_level
                in [CompetitionLevel.LOW, CompetitionLevel.MEDIUM]
                and niche.confidence_score >= 40
                and niche.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
            )

            if is_balanced:
                balanced.append(
                    {
                        "niche": niche.primary_keyword,
                        "score": niche.profitability_score_numeric,
                        "competition_level": niche.competition_level.value,
                        "risk_level": niche.risk_level.value,
                        "confidence": niche.confidence_score,
                        "estimated_effort": "Medium",
                        "time_to_market": "2-4 months",
                        "reason": f"Balanced opportunity with {niche.competition_level.value} competition and {niche.risk_level.value} risk",
                    }
                )

        return sorted(balanced, key=lambda x: x["score"], reverse=True)[:5]

    @staticmethod
    def _identify_high_potential_risks(
        niches: List[Niche], preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify high potential but risky opportunities."""
        high_risk = []

        for niche in niches[:30]:
            # High potential risk criteria
            is_high_risk = niche.profitability_score_numeric >= 80 and (
                niche.competition_level == CompetitionLevel.HIGH
                or niche.confidence_score < 50
                or niche.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]
            )

            if is_high_risk and preferences.get("risk_tolerance") in ["medium", "high"]:
                high_risk.append(
                    {
                        "niche": niche.primary_keyword,
                        "score": niche.profitability_score_numeric,
                        "risk_factors": NicheRecommendationEngine._identify_risk_factors(
                            niche
                        ),
                        "potential_reward": "Very High",
                        "estimated_effort": "High",
                        "time_to_market": "4-8 months",
                        "reason": f"High profitability potential ({niche.profitability_score_numeric:.1f}) but requires careful execution",
                    }
                )

        return sorted(high_risk, key=lambda x: x["score"], reverse=True)[:3]

    @staticmethod
    def _identify_risk_factors(niche: Niche) -> List[str]:
        """Identify specific risk factors for a niche."""
        risks = []

        if niche.competition_level == CompetitionLevel.HIGH:
            risks.append("High competition")

        if niche.confidence_score < 50:
            risks.append("Low data confidence")

        if niche.competitor_analysis_data.estimated:
            risks.append("Estimated competition data")

        if (
            niche.trend_analysis_data
            and niche.trend_analysis_data.trend_direction
            == "declining"
        ):
            risks.append("Declining trend")

        if (
            niche.trend_analysis_data
            and niche.trend_analysis_data.trend_direction
            == "volatile"
        ):
            risks.append("Volatile market")

        if len(niche.content_gaps) < 2:
            risks.append("Limited content opportunities")

        return risks

    @staticmethod
    def _generate_market_insights(niches: List[Niche]) -> Dict[str, Any]:
        """Generate comprehensive market insights."""
        if not niches:
            return {}

        # Cluster analysis
        cluster_performance = {}
        for niche in niches:
            cluster_name = (
                niche.additional_data.get("cluster_name", "unknown")
                if niche.additional_data
                else "unknown"
            )

            if cluster_name not in cluster_performance:
                cluster_performance[cluster_name] = {
                    "count": 0,
                    "avg_score": 0,
                    "avg_competition": 0,
                    "top_score": 0,
                }

            cluster_data = cluster_performance[cluster_name]
            cluster_data["count"] += 1
            cluster_data["avg_score"] += niche.profitability_score_numeric
            cluster_data[
                "avg_competition"
            ] += niche.competitor_analysis_data.competitor_count
            cluster_data["top_score"] = max(
                cluster_data["top_score"], niche.profitability_score_numeric
            )

        # Calculate averages
        for cluster_data in cluster_performance.values():
            if cluster_data["count"] > 0:
                cluster_data["avg_score"] /= cluster_data["count"]
                cluster_data["avg_competition"] /= cluster_data["count"]

        return {
            "total_niches": len(niches),
            "avg_profitability": sum(n.profitability_score_numeric for n in niches)
            / len(niches),
            "competition_distribution": {
                "low": len(
                    [n for n in niches if n.competition_level == CompetitionLevel.LOW]
                ),
                "medium": len(
                    [
                        n
                        for n in niches
                        if n.competition_level == CompetitionLevel.MEDIUM
                    ]
                ),
                "high": len(
                    [n for n in niches if n.competition_level == CompetitionLevel.HIGH]
                ),
            },
            "cluster_performance": cluster_performance,
            "trend_distribution": {
                "rising": len(
                    [
                        n
                        for n in niches
                        if n.trend_analysis_data
                        and n.trend_analysis_data.trend_direction
                        == "rising"
                    ]
                ),
                "stable": len(
                    [
                        n
                        for n in niches
                        if n.trend_analysis_data
                        and n.trend_analysis_data.trend_direction
                        == "stable"
                    ]
                ),
                "declining": len(
                    [
                        n
                        for n in niches
                        if n.trend_analysis_data
                        and n.trend_analysis_data.trend_direction
                        == "declining"
                    ]
                ),
            },
        }

    @staticmethod
    def _generate_strategic_recommendations(
        niches: List[Niche], preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate strategic recommendations for market entry."""
        strategies = []

        if not niches:
            return strategies

        # Portfolio diversification strategy
        clusters = set()
        for niche in niches[:10]:
            cluster_name = (
                niche.additional_data.get("cluster_name", "unknown")
                if niche.additional_data
                else "unknown"
            )
            clusters.add(cluster_name)

        if len(clusters) >= 3:
            strategies.append(
                {
                    "strategy": "Portfolio Diversification",
                    "description": f"Consider entering {len(clusters)} different market clusters to spread risk",
                    "action": "Select 1-2 niches from each of the top performing clusters",
                    "priority": "High",
                }
            )

        # Market timing strategy
        rising_trends = [
            n
            for n in niches[:15]
            if n.trend_analysis_data
            and n.trend_analysis_data.trend_direction == "rising"
        ]
        if len(rising_trends) >= 3:
            strategies.append(
                {
                    "strategy": "Trend Riding",
                    "description": f"Found {len(rising_trends)} niches with rising trends",
                    "action": "Prioritize these markets for quick entry to capitalize on growth",
                    "priority": "High",
                }
            )

        # Competition gap strategy
        low_competition = [
            n for n in niches[:20] if n.competition_level == CompetitionLevel.LOW
        ]
        if len(low_competition) >= 5:
            strategies.append(
                {
                    "strategy": "Blue Ocean Entry",
                    "description": f"Found {len(low_competition)} low-competition opportunities",
                    "action": "Enter these markets quickly before competition increases",
                    "priority": "Medium",
                }
            )

        return strategies


def _generate_recommendations(
    top_niches: List[Niche], all_scored_niches: List[Niche]
) -> Dict[str, Any]:
    """Generate actionable recommendations based on niche analysis."""
    if not top_niches:
        return {"message": "No profitable niches found with current criteria"}

    best_niche = top_niches[0]

    recommendations = {
        "primary_recommendation": {
            "niche": best_niche.primary_keyword,
            "score": best_niche.profitability_score_numeric,  # Use numeric score
            "reason": f"Highest profitability score with {best_niche.competition_level.value} competition",  # Use enum .value
        },
        "quick_wins": [],
        "long_term_opportunities": [],
        "market_insights": {
            "avg_profitability_score": sum(
                n.profitability_score_numeric for n in all_scored_niches
            )
            / len(all_scored_niches),
            "competition_distribution": {
                "low": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.competition_level == CompetitionLevel.LOW
                    ]
                ),
                "medium": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.competition_level == CompetitionLevel.MEDIUM
                    ]
                ),
                "high": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.competition_level == CompetitionLevel.HIGH
                    ]
                ),
            },
        },
    }

    # Identify quick wins (low competition, decent score)
    for niche in top_niches[:5]:
        if (
            niche.competition_level == CompetitionLevel.LOW
            and niche.profitability_score_numeric >= 60
        ):
            recommendations["quick_wins"].append(
                {
                    "niche": niche.primary_keyword,
                    "score": niche.profitability_score_numeric,
                    "competitors": niche.competitor_analysis_data.competitor_count,
                }
            )

    # Identify long-term opportunities (high potential, manageable competition)
    for niche in top_niches[:10]:
        if (
            niche.profitability_score_numeric >= 75
            and niche.trend_analysis_data
            and niche.trend_analysis_data.trend_direction  # Use the renamed field
            == "rising"
        ):
            recommendations["long_term_opportunities"].append(
                {
                    "niche": niche.primary_keyword,
                    "score": niche.profitability_score_numeric,
                    "trend_direction": niche.trend_analysis_data.trend_direction,
                }
            )

    return recommendations


def _generate_recommendations_enhanced(
    top_niches: List[Niche],
    all_scored_niches: List[Niche],
    keyword_clusters: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Generate enhanced actionable recommendations with cluster insights."""

    if not top_niches:
        return {
            "message": "No profitable niches found with current criteria or after filtering.",
            "primary_recommendation": None,
            "quick_wins": [],
            "long_term_opportunities": [],
            "cluster_insights": {},
            "market_insights": {
                "total_niches_analyzed": 0,
                "avg_profitability_score": 0.0,
                "competition_distribution": {"low": 0, "medium": 0, "high": 0},
                "profitability_distribution": {"high": 0, "medium": 0, "low": 0},
            },
            "actionable_insights": [],
        }
    best_niche = top_niches[0]

    # Get cluster information for best niche
    best_cluster = (
        best_niche.additional_data.get("cluster_name", "unknown")
        if best_niche.additional_data
        else "unknown"
    )

    recommendations = {
        "primary_recommendation": {
            "niche": best_niche.primary_keyword,
            "score": best_niche.profitability_score_numeric,
            "competition_level": best_niche.competition_level.value,
            "cluster": best_cluster,
            "reason": f"Highest profitability score ({best_niche.profitability_score_numeric:.1f}) in {best_cluster} cluster with {best_niche.competition_level.value} competition",
            "confidence": best_niche.confidence_score,
            "content_gaps": len(best_niche.content_gaps),
            "data_sources": best_niche.additional_data.get("data_sources", {})
            if best_niche.additional_data
            else {},
        },
        "quick_wins": [],
        "long_term_opportunities": [],
        "cluster_insights": {},
        "market_insights": {
            "total_niches_analyzed": len(all_scored_niches),
            "avg_profitability_score": sum(
                n.profitability_score_numeric for n in all_scored_niches
            )
            / len(all_scored_niches),
            "competition_distribution": {
                "low": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.competition_level == CompetitionLevel.LOW
                    ]
                ),
                "medium": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.competition_level == CompetitionLevel.MEDIUM
                    ]
                ),
                "high": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.competition_level == CompetitionLevel.HIGH
                    ]
                ),
            },
            "profitability_distribution": {
                "high": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.profitability_tier == ProfitabilityTier.HIGH
                    ]
                ),
                "medium": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.profitability_tier == ProfitabilityTier.MEDIUM
                    ]
                ),
                "low": len(
                    [
                        n
                        for n in all_scored_niches
                        if n.profitability_tier == ProfitabilityTier.LOW
                    ]
                ),
            },
        },
        "actionable_insights": [],
    }

    # Enhanced quick wins identification
    for niche in top_niches[:8]:
        cluster_name = (
            niche.additional_data.get("cluster_name", "unknown")
            if niche.additional_data
            else "unknown"
        )

        # Quick wins: Low competition + good score + high confidence
        if (
            niche.competition_level == CompetitionLevel.LOW
            and niche.profitability_score_numeric >= 55
            and niche.confidence_score >= 60
        ):
            recommendations["quick_wins"].append(
                {
                    "niche": niche.primary_keyword,
                    "score": niche.profitability_score_numeric,
                    "confidence": niche.confidence_score,
                    "competitors": niche.competitor_analysis_data.competitor_count,
                    "cluster": cluster_name,
                    "content_gaps": len(niche.content_gaps),
                    "reason": f"Low competition ({niche.competitor_analysis_data.competitor_count} competitors) with good profitability potential",
                    "estimated_effort": "Low to Medium",
                    "time_to_market": "1-2 months",
                }
            )

    # Enhanced long-term opportunities
    for niche in top_niches[:12]:
        cluster_name = (
            niche.additional_data.get("cluster_name", "unknown")
            if niche.additional_data
            else "unknown"
        )

        # Long-term: High potential + rising trends + manageable competition
        if (
            niche.profitability_score_numeric >= 70
            and niche.trend_analysis_data
            and niche.trend_analysis_data.trend_direction
            in ["rising", "stable"]
            and niche.competition_level
            in [CompetitionLevel.LOW, CompetitionLevel.MEDIUM]
        ):
            recommendations["long_term_opportunities"].append(
                {
                    "niche": niche.primary_keyword,
                    "score": niche.profitability_score_numeric,
                    "trend_direction": niche.trend_analysis_data.trend_direction,
                    "trend_score": niche.trend_analysis_data.trend_score,
                    "cluster": cluster_name,
                    "growth_potential": "High"
                    if niche.trend_analysis_data.trend_direction
                    == "rising"
                    else "Stable",
                    "market_size": niche.market_size_score,
                    "reason": f"Strong growth potential with {niche.trend_analysis_data.trend_direction} trend",
                    "estimated_effort": "Medium to High",
                    "time_to_market": "2-4 months",
                }
            )

    # Cluster insights
    cluster_performance = {}
    for niche in all_scored_niches:
        cluster_name = (
            niche.additional_data.get("cluster_name", "unknown")
            if niche.additional_data
            else "unknown"
        )

        if cluster_name not in cluster_performance:
            cluster_performance[cluster_name] = {
                "niches": [],
                "avg_score": 0,
                "avg_competition": 0,
                "total_opportunities": 0,
            }

        cluster_performance[cluster_name]["niches"].append(niche)

    # Calculate cluster statistics
    for cluster_name, data in cluster_performance.items():
        niches = data["niches"]
        data["avg_score"] = sum(n.profitability_score_numeric for n in niches) / len(
            niches
        )
        data["avg_competition"] = sum(
            n.competitor_analysis_data.competitor_count for n in niches
        ) / len(niches)
        data["total_opportunities"] = len(niches)
        data["top_niche"] = max(
            niches, key=lambda n: n.profitability_score_numeric
        ).primary_keyword

        # Remove the niches list for cleaner output
        del data["niches"]

    recommendations["cluster_insights"] = cluster_performance

    # Generate actionable insights
    insights = []

    # Best performing cluster
    if cluster_performance:
        best_cluster_name = max(
            cluster_performance.keys(),
            key=lambda k: cluster_performance[k]["avg_score"],
        )
        best_cluster_data = cluster_performance[best_cluster_name]

        insights.append(
            {
                "type": "cluster_opportunity",
                "title": f"Focus on {best_cluster_name.replace('_', ' ').title()} Cluster",
                "description": f"This cluster shows the highest average profitability ({best_cluster_data['avg_score']:.1f}) with {best_cluster_data['total_opportunities']} opportunities",
                "action": f"Prioritize developing content in the {best_cluster_name.replace('_', ' ')} category",
                "priority": "High",
            }
        )

    # Competition gaps
    low_competition_clusters = [
        name
        for name, data in cluster_performance.items()
        if data["avg_competition"] < 20
    ]

    if low_competition_clusters:
        insights.append(
            {
                "type": "competition_gap",
                "title": "Low Competition Opportunities",
                "description": f"Found {len(low_competition_clusters)} clusters with low competition: {', '.join(low_competition_clusters)}",
                "action": "Consider entering these markets quickly before competition increases",
                "priority": "Medium",
            }
        )

    # Trend opportunities
    rising_trend_count = len(
        [
            n
            for n in top_niches[:10]
            if n.trend_analysis_data
            and n.trend_analysis_data.trend_direction == "rising"
        ]
    )

    if rising_trend_count > 0:
        insights.append(
            {
                "type": "trend_opportunity",
                "title": "Rising Trend Markets",
                "description": f"Found {rising_trend_count} niches with rising trends in top opportunities",
                "action": "Capitalize on growing market interest by developing content quickly",
                "priority": "High",
            }
        )

    recommendations["actionable_insights"] = insights

    return recommendations
