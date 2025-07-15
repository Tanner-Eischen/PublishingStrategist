"""Trend Analysis data model for KDP Strategist.

Defines the TrendAnalysis class and related data structures for representing
Google Trends analysis, forecasting, and seasonal pattern detection.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
import json
import statistics


class TrendDirection(Enum):
    """Enumeration of trend directions."""
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"
    SEASONAL = "seasonal"


class SeasonalPattern(Enum):
    """Enumeration of seasonal patterns."""
    NONE = "none"
    SPRING_PEAK = "spring_peak"
    SUMMER_PEAK = "summer_peak"
    FALL_PEAK = "fall_peak"
    WINTER_PEAK = "winter_peak"
    HOLIDAY_DRIVEN = "holiday_driven"
    BACK_TO_SCHOOL = "back_to_school"
    NEW_YEAR = "new_year"
    CUSTOM = "custom"


class TrendStrength(Enum):
    """Enumeration of trend strength levels."""
    VERY_WEAK = "very_weak"  # 0-20
    WEAK = "weak"  # 21-40
    MODERATE = "moderate"  # 41-60
    STRONG = "strong"  # 61-80
    VERY_STRONG = "very_strong"  # 81-100


@dataclass
class TrendAnalysis:
    """Represents comprehensive trend analysis for a keyword or topic.
    
    This class encapsulates Google Trends data analysis, seasonal patterns,
    forecasting, and confidence metrics for market trend assessment.
    
    Attributes:
        keyword: The primary keyword or phrase analyzed
        trend_score: Overall trend strength (0-100)
        trend_direction: Direction of the trend
        trend_strength: Categorical strength assessment
        regional_interest: Interest levels by geographic region
        related_queries: Related search queries from Google Trends
        seasonal_patterns: Detected seasonal patterns and factors
        forecast_6_months: 6-month forecast values
        confidence_level: Confidence in the analysis (0-100)
        analysis_period: Time period analyzed
        data_points: Number of data points used in analysis
        volatility_score: Measure of trend volatility (0-100)
        growth_rate: Monthly growth rate percentage
        peak_periods: Identified peak interest periods
        low_periods: Identified low interest periods
    """
    
    # Core trend data
    keyword: str
    trend_score: float  # 0-100
    trend_direction: str = TrendDirection.STABLE.value
    trend_strength: str = TrendStrength.MODERATE.value
    
    # Geographic and related data
    regional_interest: Dict[str, float] = field(default_factory=dict)
    related_queries: List[str] = field(default_factory=list)
    
    # Seasonal analysis
    seasonal_patterns: Dict[str, float] = field(default_factory=dict)
    seasonal_pattern_type: str = SeasonalPattern.NONE.value
    
    # Forecasting
    forecast_6_months: List[float] = field(default_factory=list)
    confidence_level: float = 0.0
    
    # Analysis metadata
    analysis_period: str = "12m"  # e.g., "12m", "5y", "today 3-m"
    data_points: int = 0
    volatility_score: float = 0.0
    growth_rate: float = 0.0  # Monthly percentage
    
    # Peak and trend analysis
    peak_periods: List[Dict[str, Any]] = field(default_factory=list)
    low_periods: List[Dict[str, Any]] = field(default_factory=list)
    trend_breakpoints: List[Dict[str, Any]] = field(default_factory=list)
    
    # Raw data (optional, for detailed analysis)
    raw_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    analysis_date: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and process data after initialization."""
        self._validate_scores()
        self._validate_keyword()
        self._validate_forecast()
        self._determine_trend_strength()
        self.last_updated = datetime.now()
    
    def _validate_scores(self) -> None:
        """Validate that all scores are within valid ranges."""
        scores = {
            "trend_score": self.trend_score,
            "confidence_level": self.confidence_level,
            "volatility_score": self.volatility_score,
        }
        
        for score_name, score_value in scores.items():
            if not 0 <= score_value <= 100:
                raise ValueError(f"{score_name} must be between 0 and 100, got {score_value}")
    
    def _validate_keyword(self) -> None:
        """Validate keyword."""
        if not self.keyword or not self.keyword.strip():
            raise ValueError("Keyword cannot be empty")
    
    def _validate_forecast(self) -> None:
        """Validate forecast data."""
        if self.forecast_6_months:
            if len(self.forecast_6_months) != 6:
                raise ValueError("Forecast must contain exactly 6 monthly values")
            
            for value in self.forecast_6_months:
                if not 0 <= value <= 100:
                    raise ValueError("Forecast values must be between 0 and 100")
    
    def _determine_trend_strength(self) -> None:
        """Determine categorical trend strength based on score."""
        if self.trend_score <= 20:
            self.trend_strength = TrendStrength.VERY_WEAK.value
        elif self.trend_score <= 40:
            self.trend_strength = TrendStrength.WEAK.value
        elif self.trend_score <= 60:
            self.trend_strength = TrendStrength.MODERATE.value
        elif self.trend_score <= 80:
            self.trend_strength = TrendStrength.STRONG.value
        else:
            self.trend_strength = TrendStrength.VERY_STRONG.value
    
    @property
    def is_trending_up(self) -> bool:
        """Check if trend is moving upward.
        
        Returns:
            True if trend direction is rising
        """
        return self.trend_direction == TrendDirection.RISING.value
    
    @property
    def is_seasonal(self) -> bool:
        """Check if trend shows seasonal patterns.
        
        Returns:
            True if seasonal patterns are detected
        """
        return (
            self.seasonal_pattern_type != SeasonalPattern.NONE.value or
            bool(self.seasonal_patterns)
        )
    
    @property
    def is_reliable(self) -> bool:
        """Check if trend analysis is reliable.
        
        Returns:
            True if confidence level and data quality are sufficient
        """
        return (
            self.confidence_level >= 70 and
            self.data_points >= 12 and  # At least 12 data points
            self.volatility_score <= 60  # Not too volatile
        )
    
    @property
    def risk_assessment(self) -> str:
        """Assess investment risk based on trend characteristics.
        
        Returns:
            Risk level: 'low', 'medium', 'high', or 'very_high'
        """
        risk_factors = 0
        
        # High volatility increases risk
        if self.volatility_score > 70:
            risk_factors += 2
        elif self.volatility_score > 50:
            risk_factors += 1
        
        # Declining trends increase risk
        if self.trend_direction == TrendDirection.DECLINING.value:
            risk_factors += 2
        elif self.trend_direction == TrendDirection.VOLATILE.value:
            risk_factors += 1
        
        # Low confidence increases risk
        if self.confidence_level < 50:
            risk_factors += 2
        elif self.confidence_level < 70:
            risk_factors += 1
        
        # Low trend score increases risk
        if self.trend_score < 30:
            risk_factors += 1
        
        if risk_factors >= 5:
            return "very_high"
        elif risk_factors >= 3:
            return "high"
        elif risk_factors >= 1:
            return "medium"
        else:
            return "low"
    
    @property
    def opportunity_score(self) -> float:
        """Calculate overall opportunity score.
        
        Returns:
            Weighted opportunity score (0-100)
        """
        # Base score from trend strength
        base_score = self.trend_score * 0.4
        
        # Bonus for rising trends
        direction_bonus = 0
        if self.trend_direction == TrendDirection.RISING.value:
            direction_bonus = 20
        elif self.trend_direction == TrendDirection.STABLE.value:
            direction_bonus = 10
        
        # Confidence factor
        confidence_factor = self.confidence_level * 0.3
        
        # Volatility penalty
        volatility_penalty = self.volatility_score * 0.1
        
        opportunity = base_score + direction_bonus + confidence_factor - volatility_penalty
        return round(max(0, min(100, opportunity)), 1)
    
    def add_peak_period(self, start_date: datetime, end_date: datetime, peak_value: float, description: str = "") -> None:
        """Add a peak period to the analysis.
        
        Args:
            start_date: Start of peak period
            end_date: End of peak period
            peak_value: Peak interest value
            description: Optional description of the peak
        """
        peak_info = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "peak_value": peak_value,
            "description": description,
            "duration_days": (end_date - start_date).days,
        }
        self.peak_periods.append(peak_info)
    
    def add_low_period(self, start_date: datetime, end_date: datetime, low_value: float, description: str = "") -> None:
        """Add a low period to the analysis.
        
        Args:
            start_date: Start of low period
            end_date: End of low period
            low_value: Low interest value
            description: Optional description of the low period
        """
        low_info = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "low_value": low_value,
            "description": description,
            "duration_days": (end_date - start_date).days,
        }
        self.low_periods.append(low_info)
    
    def set_seasonal_factor(self, month: str, factor: float) -> None:
        """Set seasonal factor for a specific month.
        
        Args:
            month: Month name (e.g., 'January', 'February')
            factor: Seasonal multiplier (1.0 = normal, >1.0 = higher interest)
        """
        if not 0 <= factor <= 5.0:
            raise ValueError("Seasonal factor must be between 0 and 5.0")
        self.seasonal_patterns[month] = factor
    
    def get_forecast_trend(self) -> str:
        """Analyze forecast trend direction.
        
        Returns:
            Forecast trend: 'improving', 'stable', 'declining'
        """
        if not self.forecast_6_months or len(self.forecast_6_months) < 2:
            return "unknown"
        
        # Calculate trend from first to last forecast value
        first_half = statistics.mean(self.forecast_6_months[:3])
        second_half = statistics.mean(self.forecast_6_months[3:])
        
        change_percent = ((second_half - first_half) / first_half) * 100 if first_half > 0 else 0
        
        if change_percent > 5:
            return "improving"
        elif change_percent < -5:
            return "declining"
        else:
            return "stable"
    
    def get_best_months(self, limit: int = 3) -> List[Tuple[str, float]]:
        """Get months with highest seasonal interest.
        
        Args:
            limit: Maximum number of months to return
            
        Returns:
            List of (month, factor) tuples sorted by factor
        """
        if not self.seasonal_patterns:
            return []
        
        sorted_months = sorted(
            self.seasonal_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_months[:limit]
    
    def get_worst_months(self, limit: int = 3) -> List[Tuple[str, float]]:
        """Get months with lowest seasonal interest.
        
        Args:
            limit: Maximum number of months to return
            
        Returns:
            List of (month, factor) tuples sorted by factor (ascending)
        """
        if not self.seasonal_patterns:
            return []
        
        sorted_months = sorted(
            self.seasonal_patterns.items(),
            key=lambda x: x[1]
        )
        
        return sorted_months[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trend analysis to dictionary for serialization.
        
        Returns:
            Dictionary representation of the trend analysis
        """
        return {
            "keyword": self.keyword,
            "trend_score": self.trend_score,
            "trend_direction": self.trend_direction,
            "trend_strength": self.trend_strength,
            "regional_interest": self.regional_interest,
            "related_queries": self.related_queries,
            "seasonal_patterns": self.seasonal_patterns,
            "seasonal_pattern_type": self.seasonal_pattern_type,
            "forecast_6_months": self.forecast_6_months,
            "confidence_level": self.confidence_level,
            "analysis_period": self.analysis_period,
            "data_points": self.data_points,
            "volatility_score": self.volatility_score,
            "growth_rate": self.growth_rate,
            "peak_periods": self.peak_periods,
            "low_periods": self.low_periods,
            "trend_breakpoints": self.trend_breakpoints,
            "analysis_date": self.analysis_date.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "additional_data": self.additional_data,
            "is_trending_up": self.is_trending_up,
            "is_seasonal": self.is_seasonal,
            "is_reliable": self.is_reliable,
            "risk_assessment": self.risk_assessment,
            "opportunity_score": self.opportunity_score,
            "forecast_trend": self.get_forecast_trend(),
            "best_months": self.get_best_months(),
            "worst_months": self.get_worst_months(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrendAnalysis":
        """Create trend analysis from dictionary.
        
        Args:
            data: Dictionary containing trend analysis data
            
        Returns:
            TrendAnalysis instance
        """
        # Handle datetime conversion
        for date_field in ["analysis_date", "last_updated"]:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])
        
        # Remove computed properties
        computed_fields = {
            "is_trending_up", "is_seasonal", "is_reliable", "risk_assessment",
            "opportunity_score", "forecast_trend", "best_months", "worst_months"
        }
        filtered_data = {k: v for k, v in data.items() if k not in computed_fields}
        
        return cls(**filtered_data)
    
    def to_json(self) -> str:
        """Convert trend analysis to JSON string.
        
        Returns:
            JSON representation of the trend analysis
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "TrendAnalysis":
        """Create trend analysis from JSON string.
        
        Args:
            json_str: JSON string containing trend analysis data
            
        Returns:
            TrendAnalysis instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation of the trend analysis."""
        return f"TrendAnalysis(keyword='{self.keyword}', score={self.trend_score}, direction='{self.trend_direction}')"
    
    def __repr__(self) -> str:
        """Detailed string representation of the trend analysis."""
        return (
            f"TrendAnalysis(keyword='{self.keyword}', score={self.trend_score}, "
            f"direction='{self.trend_direction}', confidence={self.confidence_level}, "
            f"opportunity={self.opportunity_score})"
        )