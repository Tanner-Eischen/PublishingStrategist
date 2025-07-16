"""Niche data model for KDP Strategist.

Defines the Niche class and related data structures for representing
market niches with scoring, competition analysis, and profitability metrics.
"""

from dataclasses import dataclass, field, asdict
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
class PriceRange:
    """Simple price range representation."""
    min: float = 0.0
    max: float = 0.0
    avg: float = 0.0


@dataclass
class MarketSummary:
    """Summary of competitor landscape for a niche."""
    competitor_count: int = 0
    avg_review_count: float = 0.0
    avg_rating: float = 0.0
    price_range: PriceRange = field(default_factory=PriceRange)
    estimated: bool = False


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
        top_competitors: List of top competitor ASINs
        recommended_price_range: Suggested pricing range (min, max)
        content_gaps: Identified gaps in existing content
        analysis_date: When this analysis was performed
        confidence_score: Confidence in the analysis (0-100)
        market_size_score: Overall market size assessment (0-100)
        seasonal_factors: Seasonal considerations for the niche
    """
    
    
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
    trend_analysis_data: Optional[TrendAnalysis] = None  # Renamed, store TrendAnalysis object
    competitor_analysis_data: MarketSummary = field(default_factory=MarketSummary)
    seasonal_factors: Dict[str, float] = field(default_factory=dict)
    content_gaps: List[str] = field(default_factory=list)

        # Other relevant niche attributes
    recommended_price_range: Tuple[float, float] = (9.99, 19.99)
    top_competitors: List[str] = field(default_factory=list) # ASINs

        # Metadata
    analysis_date: datetime = field(default_factory=datetime.now)
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
            self._validate_scores()
            self._validate_keywords()
            self._validate_price_range()
            # Auto-assign categorical levels if numeric scores are provided
            if self.competition_score_numeric != 0.0:
                self.competition_level = self._determine_competition_level(self.competition_score_numeric)
            if self.profitability_score_numeric != 0.0:
                self.profitability_tier = self._determine_profitability_tier(self.profitability_score_numeric)

        # Static methods to determine enum from numeric score (can be moved outside if preferred)
    @staticmethod
    def _determine_competition_level(score: float) -> CompetitionLevel:
            if score <= 30: return CompetitionLevel.LOW
            elif score <= 60: return CompetitionLevel.MEDIUM
            else: return CompetitionLevel.HIGH

    @staticmethod
    def _determine_profitability_tier(score: float) -> ProfitabilityTier:
            if score >= 80: return ProfitabilityTier.HIGH
            elif score >= 60: return ProfitabilityTier.MEDIUM
            else: return ProfitabilityTier.LOW

    @property
    def overall_score(self) -> float:
            # Use numeric score fields
            profitability_weight = 0.4
            competition_weight = 0.3
            market_size_weight = 0.2
            confidence_weight = 0.1
            adjusted_competition = 100 - self.competition_score_numeric
            weighted_score = (
                self.profitability_score_numeric * profitability_weight +
                adjusted_competition * competition_weight +
                self.market_size_score * market_size_weight +
                self.confidence_score * confidence_weight
            )
            return round(weighted_score, 2)

        # Removed `is_profitable` property as `profitability_tier` provides this classification
   
        
    
    @property
    def risk_level(self) -> RiskLevel:
            """Assess risk level for this niche, returning a RiskLevel enum."""
            if (self.competition_score_numeric <= 30 and self.confidence_score >= 80 and
                self.profitability_tier == ProfitabilityTier.HIGH):
                return RiskLevel.LOW
            elif (self.competition_score_numeric <= 60 and self.confidence_score >= 60 and
                  self.profitability_tier in [ProfitabilityTier.HIGH, ProfitabilityTier.MEDIUM]):
                return RiskLevel.MEDIUM
            elif self.overall_score >= 40:
                return RiskLevel.HIGH
            else:
                return RiskLevel.VERY_HIGH
    
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
            data = {
                "category": self.category,
                "subcategory": self.subcategory,
                "primary_keyword": self.primary_keyword,
                "keywords": self.keywords,
                "competition_score_numeric": self.competition_score_numeric,
                "profitability_score_numeric": self.profitability_score_numeric,
                "confidence_score": self.confidence_score,
                "market_size_score": self.market_size_score,
                "competition_level": self.competition_level.value, # Serialize enum value
                "profitability_tier": self.profitability_tier.value, # Serialize enum value
                "trend_analysis_data": self.trend_analysis_data.to_dict() if self.trend_analysis_data else None, # Serialize nested dataclass
                "competitor_analysis_data": asdict(self.competitor_analysis_data),
                "seasonal_factors": self.seasonal_factors,
                "content_gaps": self.content_gaps,
                "recommended_price_range": list(self.recommended_price_range),
                "top_competitors": self.top_competitors,
                "analysis_date": self.analysis_date.isoformat(),
                "additional_data": self.additional_data,
                "overall_score": self.overall_score, # Include computed properties
                "risk_level": self.risk_level.value, # Include computed properties
            }
            return data

    
    def to_json(self) -> str:
        """Convert niche to JSON string.
        
        Returns:
            JSON representation of the niche
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Niche":
            # Handle datetime, tuple conversions
            if "analysis_date" in data and isinstance(data["analysis_date"], str):
                data["analysis_date"] = datetime.fromisoformat(data["analysis_date"])
            if "recommended_price_range" in data and isinstance(data["recommended_price_range"], list):
                data["recommended_price_range"] = tuple(data["recommended_price_range"])

            # Deserialize enums
            if "competition_level" in data and isinstance(data["competition_level"], str):
                data["competition_level"] = CompetitionLevel(data["competition_level"])
            if "profitability_tier" in data and isinstance(data["profitability_tier"], str):
                data["profitability_tier"] = ProfitabilityTier(data["profitability_tier"])
            if "risk_level" in data and isinstance(data["risk_level"], str): # Deserialize if stored
                data.pop("risk_level") # This is a computed property, remove before init

            # Deserialize nested TrendAnalysis object
            if "trend_analysis_data" in data and data["trend_analysis_data"] is not None:
                data["trend_analysis_data"] = TrendAnalysis.from_dict(data["trend_analysis_data"])
            elif "trend_analysis" in data: # Handle old naming if exists
                 if data["trend_analysis"] is not None:
                    data["trend_analysis_data"] = TrendAnalysis.from_dict(data["trend_analysis"])
                 data.pop("trend_analysis") # Remove old key

            # Deserialize competitor analysis data
            if "competitor_analysis_data" in data and isinstance(data["competitor_analysis_data"], dict):
                cad = data["competitor_analysis_data"]
                price_range = cad.get("price_range", {})
                data["competitor_analysis_data"] = MarketSummary(
                    competitor_count=cad.get("competitor_count", 0),
                    avg_review_count=cad.get("avg_review_count", 0.0),
                    avg_rating=cad.get("avg_rating", 0.0),
                    price_range=PriceRange(
                        min=price_range.get("min", 0.0),
                        max=price_range.get("max", 0.0),
                        avg=price_range.get("avg", 0.0),
                    ),
                    estimated=cad.get("estimated", False),
                )

            # Rename old score keys if present
            if 'competition_score' in data and 'competition_score_numeric' not in data:
                data['competition_score_numeric'] = data.pop('competition_score')
            if 'profitability_score' in data and 'profitability_score_numeric' not in data:
                data['profitability_score_numeric'] = data.pop('profitability_score')

            # Remove computed properties and old redundant fields before passing to constructor
            computed_fields = {"overall_score"}
            filtered_data = {k: v for k, v in data.items() if k not in computed_fields}
            filtered_data.pop('trend_direction', None) # Remove if it was serialized
            filtered_data.pop('estimated_monthly_searches', None) # Remove if it was serialized

            return cls(**filtered_data)
