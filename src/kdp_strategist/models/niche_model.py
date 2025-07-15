"""Niche data model for KDP Strategist.

Defines the Niche class and related data structures for representing
market niches with scoring, competition analysis, and profitability metrics.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import json
from src.kdp_strategist.models.trend_model import TrendAnalysis

class CompetitionLevel(Enum):
        """Categorical representation of market competition."""
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

class ProfitabilityTier(Enum):
        """Categorical representation of niche profitability."""
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

class RiskLevel(Enum): # NEW: Introduce a RiskLevel enum for consistency
        """Categorical representation of niche risk."""
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        VERY_HIGH = "very_high"
class NicheCategory(Enum):
    """Enumeration of major KDP categories."""
    BUSINESS = "Business & Money"
    SELF_HELP = "Self-Help"
    HEALTH_FITNESS = "Health, Fitness & Dieting"
    COOKING = "Cookbooks, Food & Wine"
    CRAFTS_HOBBIES = "Crafts, Hobbies & Home"
    PARENTING = "Parenting & Relationships"
    EDUCATION = "Education & Teaching"
    TECHNOLOGY = "Computers & Technology"
    TRAVEL = "Travel"
    FICTION = "Literature & Fiction"
    ROMANCE = "Romance"
    MYSTERY = "Mystery, Thriller & Suspense"
    FANTASY = "Science Fiction & Fantasy"
    CHILDREN = "Children's Books"
    YOUNG_ADULT = "Teen & Young Adult"
    RELIGION = "Religion & Spirituality"
    HISTORY = "History"
    BIOGRAPHY = "Biographies & Memoirs"
    POLITICS = "Politics & Social Sciences"
    ARTS = "Arts & Photography"


@dataclass
class Niche:
    """Represents a market niche with comprehensive analysis data.
    
    This class encapsulates all information about a potential publishing niche,
    including market metrics, competition analysis, and profitability scoring.
    
    Attributes:
        category: Primary category for the niche
        subcategory: More specific subcategory
        keywords: List of relevant keywords for the niche
        competition_score: Competition intensity (0-100, lower is better)
        profitability_score: Profit potential (0-100, higher is better)
        trend_direction: Overall trend direction
        estimated_monthly_searches: Estimated search volume per month
        top_competitors: List of top competitor ASINs
        recommended_price_range: Suggested pricing range (min, max)
        content_gaps: Identified gaps in existing content
        analysis_date: When this analysis was performed
        confidence_score: Confidence in the analysis (0-100)
        market_size_score: Overall market size assessment (0-100)
        seasonal_factors: Seasonal considerations for the niche
    """
    
    @dataclass
    class Niche:
        # Core identification
        category: str # Consider making this NicheCategory if strict
        primary_keyword: str # Added: crucial for identification, used in discovery/testing
        subcategory: str = ""
        keywords: List[str] = field(default_factory=list)

        # Raw Numeric Scores (0-100 scale)
        competition_score_numeric: float = 0.0 # Renamed
        profitability_score_numeric: float = 0.0 # Renamed
        market_size_score: float = 0.0
        confidence_score: float = 0.0

        # Categorical Levels (derived from numeric scores)
        competition_level: CompetitionLevel = CompetitionLevel.MEDIUM # NEW field
        profitability_tier: ProfitabilityTier = ProfitabilityTier.MEDIUM # NEW field

        # Detailed Analysis Data (store objects or dicts for flexibility)
        trend_analysis_data: Optional[TrendAnalysis] = None # Renamed, store TrendAnalysis object
        competitor_analysis_data: Dict[str, Any] = field(default_factory=dict) # Added, matches usage
        seasonal_factors: Dict[str, float] = field(default_factory=dict)
        content_gaps: List[str] = field(default_factory=list)

        # Other relevant niche attributes
        recommended_price_range: Tuple[float, float] = (9.99, 19.99)
        top_competitors: List[str] = field(default_factory=list) # ASINs

        # Metadata
        analysis_date: datetime = field(default_factory=datetime.now)
        additional_data: Dict[str, Any] = field(default_factory=dict)ict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate data after initialization."""
        self._validate_scores()
        self._validate_keywords()
        self._validate_price_range()
        self._validate_trend_direction()
    
    def _validate_scores(self) -> None:
        """Validate that all scores are within valid ranges."""
        scores = {
            "competition_score": self.competition_score_numeric,
            "profitability_score": self.profitability_score,
            "confidence_score": self.confidence_score,
            "market_size_score": self.market_size_score,
        }
        
        for score_name, score_value in scores.items():
            if not 0 <= score_value <= 100:
                raise ValueError(f"{score_name} must be between 0 and 100, got {score_value}")
    
    def _validate_keywords(self) -> None:
        """Validate keywords list."""
        if not self.keywords:
            raise ValueError("Keywords list cannot be empty")
        
        if len(self.keywords) > 50:
            raise ValueError("Too many keywords (max 50)")
        
        for keyword in self.keywords:
            if not isinstance(keyword, str) or not keyword.strip():
                raise ValueError("All keywords must be non-empty strings")
    
    def _validate_price_range(self) -> None:
        """Validate price range."""
        min_price, max_price = self.recommended_price_range
        if min_price <= 0 or max_price <= 0:
            raise ValueError("Prices must be positive")
        if min_price >= max_price:
            raise ValueError("Minimum price must be less than maximum price")
    
    def _validate_trend_direction(self) -> None:
        """Validate trend direction."""
        valid_directions = {"rising", "stable", "declining"}
        if self.trend_direction not in valid_directions:
            raise ValueError(f"Trend direction must be one of {valid_directions}")
    
    @property
    def overall_score(self) -> float:
        """Calculate overall niche score based on weighted metrics.
        
        Returns:
            Weighted score combining profitability, competition, and market size
        """
        # Weights for different factors
        profitability_weight = 0.4
        competition_weight = 0.3  # Lower competition is better, so invert
        market_size_weight = 0.2
        confidence_weight = 0.1
        
        # Invert competition score (lower competition = higher score)
        adjusted_competition = 100 - self.competition_score
        
        weighted_score = (
            self.profitability_score * profitability_weight +
            adjusted_competition * competition_weight +
            self.market_size_score * market_size_weight +
            self.confidence_score * confidence_weight
        )
        
        return round(weighted_score, 2)
    
    @property
    def is_profitable(self) -> bool:
        """Check if niche meets profitability criteria.
        
        Returns:
            True if niche is considered profitable
        """
        return (
            self.profitability_score >= 50 and
            self.competition_score <= 70 and
            self.confidence_score >= 60
        )
    
    @property
    def risk_level(self) -> str:
        """Assess risk level for this niche.
        
        Returns:
            Risk level: 'low', 'medium', or 'high'
        """
        if self.competition_score <= 30 and self.confidence_score >= 80:
            return "low"
        elif self.competition_score <= 60 and self.confidence_score >= 60:
            return "medium"
        else:
            return "high"
    
    def get_primary_keywords(self, limit: int = 5) -> List[str]:
        """Get the most important keywords for this niche.
        
        Args:
            limit: Maximum number of keywords to return
            
        Returns:
            List of primary keywords
        """
        return self.keywords[:limit]
    
    def add_competitor(self, asin: str) -> None:
        """Add a competitor ASIN to the analysis.
        
        Args:
            asin: Amazon Standard Identification Number
        """
        if asin and asin not in self.top_competitors:
            self.top_competitors.append(asin)
    
    def add_content_gap(self, gap: str) -> None:
        """Add an identified content gap.
        
        Args:
            gap: Description of the content gap
        """
        if gap and gap not in self.content_gaps:
            self.content_gaps.append(gap)
    
    def set_seasonal_factor(self, month: str, factor: float) -> None:
        """Set seasonal factor for a specific month.
        
        Args:
            month: Month name (e.g., 'January', 'February')
            factor: Seasonal multiplier (1.0 = normal, >1.0 = higher demand)
        """
        if not 0 <= factor <= 5.0:
            raise ValueError("Seasonal factor must be between 0 and 5.0")
        self.seasonal_factors[month] = factor
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert niche to dictionary for serialization.
        
        Returns:
            Dictionary representation of the niche
        """
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "keywords": self.keywords,
            "competition_score": self.competition_score,
            "profitability_score": self.profitability_score,
            "confidence_score": self.confidence_score,
            "market_size_score": self.market_size_score,
            "trend_direction": self.trend_direction,
            "estimated_monthly_searches": self.estimated_monthly_searches,
            "top_competitors": self.top_competitors,
            "recommended_price_range": list(self.recommended_price_range),
            "content_gaps": self.content_gaps,
            "seasonal_factors": self.seasonal_factors,
            "analysis_date": self.analysis_date.isoformat(),
            "additional_data": self.additional_data,
            "overall_score": self.overall_score,
            "is_profitable": self.is_profitable,
            "risk_level": self.risk_level,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Niche":
        """Create niche from dictionary.
        
        Args:
            data: Dictionary containing niche data
            
        Returns:
            Niche instance
        """
        # Handle datetime conversion
        if "analysis_date" in data and isinstance(data["analysis_date"], str):
            data["analysis_date"] = datetime.fromisoformat(data["analysis_date"])
        
        # Handle tuple conversion for price range
        if "recommended_price_range" in data and isinstance(data["recommended_price_range"], list):
            data["recommended_price_range"] = tuple(data["recommended_price_range"])
        
        # Remove computed properties
        computed_fields = {"overall_score", "is_profitable", "risk_level"}
        filtered_data = {k: v for k, v in data.items() if k not in computed_fields}
        
        return cls(**filtered_data)
    
    def to_json(self) -> str:
        """Convert niche to JSON string.
        
        Returns:
            JSON representation of the niche
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Niche":
        """Create niche from JSON string.
        
        Args:
            json_str: JSON string containing niche data
            
        Returns:
            Niche instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation of the niche."""
        return f"Niche(category='{self.category}', subcategory='{self.subcategory}', score={self.overall_score})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the niche."""
        return (
            f"Niche(category='{self.category}', subcategory='{self.subcategory}', "
            f"keywords={len(self.keywords)}, profitability={self.profitability_score}, "
            f"competition={self.competition_score}, overall_score={self.overall_score})"
        )