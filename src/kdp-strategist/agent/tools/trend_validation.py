"""Trend Validation Tool.

Validates and analyzes market trends to assess:
- Trend strength and sustainability
- Seasonal patterns and cyclical behavior
- Growth trajectory and momentum
- Market timing opportunities
- Risk factors and volatility
- Future trend forecasting

The tool provides comprehensive trend analysis including:
- Historical trend validation
- Seasonal decomposition
- Trend forecasting models
- Risk assessment metrics
- Market timing recommendations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from statistics import mean, stdev
import math

from ...data.cache_manager import CacheManager
from ...data.trends_client import TrendsClient, TrendData
from ...models.trend_model import TrendAnalysis, TrendDirection, TrendStrength
from ...models.niche_model import Niche

logger = logging.getLogger(__name__)


@dataclass
class SeasonalPattern:
    """Represents a seasonal pattern in trend data."""
    season: str  # spring, summer, fall, winter
    months: List[int]
    avg_intensity: float
    peak_month: int
    volatility: float
    reliability_score: float


@dataclass
class TrendForecast:
    """Forecast data for future trend performance."""
    timeframe: str  # "1_month", "3_months", "6_months", "12_months"
    predicted_score: float
    confidence_interval: Tuple[float, float]
    direction: TrendDirection
    key_factors: List[str]
    risk_level: str


@dataclass
class ValidationResult:
    """Complete trend validation result."""
    keyword: str
    is_valid: bool
    strength_score: float
    sustainability_score: float
    seasonal_analysis: Dict[str, Any]
    forecasts: List[TrendForecast]
    risk_factors: List[str]
    opportunities: List[str]
    recommendations: List[str]
    validation_timestamp: datetime


class TrendValidator:
    """Core trend validation and analysis engine."""
    
    # Validation thresholds
    MIN_TREND_SCORE = 20
    MIN_DATA_POINTS = 12  # Minimum months of data
    MAX_VOLATILITY = 0.8  # Maximum acceptable volatility
    MIN_CONFIDENCE = 0.3
    
    @classmethod
    def validate_trend_strength(
        cls,
        trend_analysis: TrendAnalysis,
        historical_data: Optional[List[TrendData]] = None
    ) -> Dict[str, Any]:
        """Validate the strength and reliability of a trend."""
        validation = {
            "is_strong": False,
            "strength_score": 0.0,
            "reliability_factors": [],
            "weakness_factors": []
        }
        
        # Base strength from trend score
        base_strength = trend_analysis.trend_score
        validation["strength_score"] = base_strength
        
        # Check minimum threshold
        if base_strength < cls.MIN_TREND_SCORE:
            validation["weakness_factors"].append(f"Trend score {base_strength} below minimum threshold {cls.MIN_TREND_SCORE}")
            return validation
        
        # Validate confidence level
        if trend_analysis.confidence_level < cls.MIN_CONFIDENCE:
            validation["weakness_factors"].append(f"Low confidence level: {trend_analysis.confidence_level:.2f}")
        else:
            validation["reliability_factors"].append(f"Good confidence level: {trend_analysis.confidence_level:.2f}")
        
        # Validate trend direction
        if trend_analysis.direction == TrendDirection.RISING:
            validation["reliability_factors"].append("Positive trend direction")
            validation["strength_score"] *= 1.1
        elif trend_analysis.direction == TrendDirection.DECLINING:
            validation["weakness_factors"].append("Declining trend direction")
            validation["strength_score"] *= 0.8
        
        # Validate trend strength category
        if trend_analysis.strength in [TrendStrength.STRONG, TrendStrength.VERY_STRONG]:
            validation["reliability_factors"].append(f"Strong trend classification: {trend_analysis.strength.value}")
            validation["strength_score"] *= 1.2
        elif trend_analysis.strength == TrendStrength.WEAK:
            validation["weakness_factors"].append(f"Weak trend classification: {trend_analysis.strength.value}")
            validation["strength_score"] *= 0.7
        
        # Historical data validation
        if historical_data and len(historical_data) >= cls.MIN_DATA_POINTS:
            historical_validation = cls._validate_historical_consistency(historical_data)
            validation["reliability_factors"].extend(historical_validation["strengths"])
            validation["weakness_factors"].extend(historical_validation["weaknesses"])
            validation["strength_score"] *= historical_validation["consistency_multiplier"]
        
        # Final determination
        validation["is_strong"] = (
            validation["strength_score"] >= cls.MIN_TREND_SCORE * 1.5 and
            len(validation["weakness_factors"]) <= len(validation["reliability_factors"])
        )
        
        return validation
    
    @classmethod
    def _validate_historical_consistency(
        cls,
        historical_data: List[TrendData]
    ) -> Dict[str, Any]:
        """Validate consistency in historical trend data."""
        if len(historical_data) < 3:
            return {
                "strengths": [],
                "weaknesses": ["Insufficient historical data"],
                "consistency_multiplier": 0.8
            }
        
        # Extract trend scores over time
        scores = [data.trend_score for data in historical_data if data.trend_score is not None]
        
        if len(scores) < 3:
            return {
                "strengths": [],
                "weaknesses": ["Insufficient trend score data"],
                "consistency_multiplier": 0.8
            }
        
        # Calculate consistency metrics
        avg_score = mean(scores)
        score_stdev = stdev(scores) if len(scores) > 1 else 0
        volatility = score_stdev / avg_score if avg_score > 0 else 1
        
        strengths = []
        weaknesses = []
        multiplier = 1.0
        
        # Volatility analysis
        if volatility <= 0.2:
            strengths.append("Very stable trend with low volatility")
            multiplier *= 1.1
        elif volatility <= 0.4:
            strengths.append("Moderately stable trend")
        elif volatility <= cls.MAX_VOLATILITY:
            weaknesses.append("Moderate volatility in trend")
            multiplier *= 0.95
        else:
            weaknesses.append(f"High volatility: {volatility:.2f}")
            multiplier *= 0.8
        
        # Trend progression analysis
        if len(scores) >= 6:
            recent_avg = mean(scores[-3:])
            older_avg = mean(scores[:3])
            
            if recent_avg > older_avg * 1.1:
                strengths.append("Improving trend over time")
                multiplier *= 1.1
            elif recent_avg < older_avg * 0.9:
                weaknesses.append("Declining trend over time")
                multiplier *= 0.9
        
        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "consistency_multiplier": multiplier
        }
    
    @classmethod
    def analyze_seasonality(
        cls,
        trend_analysis: TrendAnalysis,
        historical_data: Optional[List[TrendData]] = None
    ) -> Dict[str, Any]:
        """Analyze seasonal patterns in trend data."""
        seasonal_analysis = {
            "has_seasonality": False,
            "seasonality_strength": 0.0,
            "seasonal_patterns": [],
            "peak_seasons": [],
            "low_seasons": [],
            "seasonal_risk": "low"
        }
        
        # Use existing seasonal patterns from trend analysis
        if trend_analysis.seasonal_patterns:
            seasonal_analysis["has_seasonality"] = True
            seasonal_analysis.update(trend_analysis.seasonal_patterns)
        
        # Enhanced analysis with historical data
        if historical_data and len(historical_data) >= 12:
            enhanced_seasonal = cls._analyze_historical_seasonality(historical_data)
            seasonal_analysis.update(enhanced_seasonal)
        
        # Determine seasonal risk level
        seasonality_strength = seasonal_analysis.get("seasonality_strength", 0)
        if seasonality_strength > 0.7:
            seasonal_analysis["seasonal_risk"] = "high"
        elif seasonality_strength > 0.4:
            seasonal_analysis["seasonal_risk"] = "medium"
        else:
            seasonal_analysis["seasonal_risk"] = "low"
        
        return seasonal_analysis
    
    @classmethod
    def _analyze_historical_seasonality(
        cls,
        historical_data: List[TrendData]
    ) -> Dict[str, Any]:
        """Analyze seasonality from historical data points."""
        # Group data by month
        monthly_scores = {i: [] for i in range(1, 13)}
        
        for data_point in historical_data:
            if data_point.date and data_point.trend_score is not None:
                month = data_point.date.month
                monthly_scores[month].append(data_point.trend_score)
        
        # Calculate monthly averages
        monthly_averages = {}
        for month, scores in monthly_scores.items():
            if scores:
                monthly_averages[month] = mean(scores)
        
        if len(monthly_averages) < 6:  # Need at least 6 months
            return {"seasonality_strength": 0.0}
        
        # Calculate seasonality metrics
        avg_scores = list(monthly_averages.values())
        overall_avg = mean(avg_scores)
        max_score = max(avg_scores)
        min_score = min(avg_scores)
        
        # Seasonality strength (coefficient of variation)
        score_stdev = stdev(avg_scores) if len(avg_scores) > 1 else 0
        seasonality_strength = score_stdev / overall_avg if overall_avg > 0 else 0
        
        # Identify peak and low seasons
        peak_months = [month for month, score in monthly_averages.items() 
                      if score >= max_score * 0.9]
        low_months = [month for month, score in monthly_averages.items() 
                     if score <= min_score * 1.1]
        
        # Create seasonal patterns
        seasonal_patterns = cls._create_seasonal_patterns(monthly_averages)
        
        return {
            "seasonality_strength": min(1.0, seasonality_strength),
            "monthly_averages": monthly_averages,
            "peak_months": peak_months,
            "low_months": low_months,
            "seasonal_patterns": seasonal_patterns
        }
    
    @classmethod
    def _create_seasonal_patterns(
        cls,
        monthly_averages: Dict[int, float]
    ) -> List[SeasonalPattern]:
        """Create seasonal pattern objects from monthly data."""
        # Define seasons
        seasons = {
            "spring": [3, 4, 5],
            "summer": [6, 7, 8],
            "fall": [9, 10, 11],
            "winter": [12, 1, 2]
        }
        
        patterns = []
        
        for season_name, months in seasons.items():
            season_scores = [monthly_averages.get(month, 0) for month in months 
                           if month in monthly_averages]
            
            if season_scores:
                avg_intensity = mean(season_scores)
                peak_month = months[season_scores.index(max(season_scores))]
                volatility = stdev(season_scores) / avg_intensity if len(season_scores) > 1 and avg_intensity > 0 else 0
                
                # Calculate reliability based on data availability and consistency
                reliability = min(1.0, len(season_scores) / 3 * (1 - min(volatility, 1.0)))
                
                pattern = SeasonalPattern(
                    season=season_name,
                    months=months,
                    avg_intensity=avg_intensity,
                    peak_month=peak_month,
                    volatility=volatility,
                    reliability_score=reliability
                )
                patterns.append(pattern)
        
        return patterns
    
    @classmethod
    def generate_forecasts(
        cls,
        trend_analysis: TrendAnalysis,
        historical_data: Optional[List[TrendData]] = None,
        seasonal_analysis: Optional[Dict[str, Any]] = None
    ) -> List[TrendForecast]:
        """Generate trend forecasts for different timeframes."""
        forecasts = []
        
        # Base forecast parameters
        current_score = trend_analysis.trend_score
        current_direction = trend_analysis.direction
        confidence = trend_analysis.confidence_level
        
        # Forecast timeframes
        timeframes = [
            ("1_month", 30),
            ("3_months", 90),
            ("6_months", 180),
            ("12_months", 365)
        ]
        
        for timeframe_name, days in timeframes:
            forecast = cls._generate_single_forecast(
                timeframe_name,
                days,
                current_score,
                current_direction,
                confidence,
                historical_data,
                seasonal_analysis
            )
            forecasts.append(forecast)
        
        return forecasts
    
    @classmethod
    def _generate_single_forecast(
        cls,
        timeframe: str,
        days: int,
        current_score: float,
        current_direction: TrendDirection,
        confidence: float,
        historical_data: Optional[List[TrendData]] = None,
        seasonal_analysis: Optional[Dict[str, Any]] = None
    ) -> TrendForecast:
        """Generate a single forecast for a specific timeframe."""
        # Base prediction
        predicted_score = current_score
        
        # Apply trend direction
        direction_multipliers = {
            TrendDirection.RISING: 1.1,
            TrendDirection.STABLE: 1.0,
            TrendDirection.DECLINING: 0.9
        }
        
        base_multiplier = direction_multipliers.get(current_direction, 1.0)
        
        # Apply time decay (longer forecasts are less reliable)
        time_decay = 1.0 - (days / 365) * 0.2  # Max 20% decay over 1 year
        
        # Apply historical trend if available
        historical_multiplier = 1.0
        if historical_data and len(historical_data) >= 6:
            historical_multiplier = cls._calculate_historical_trend_multiplier(historical_data)
        
        # Apply seasonal adjustment
        seasonal_multiplier = 1.0
        if seasonal_analysis and seasonal_analysis.get("has_seasonality"):
            seasonal_multiplier = cls._calculate_seasonal_multiplier(
                seasonal_analysis, days
            )
        
        # Calculate final prediction
        predicted_score = current_score * base_multiplier * time_decay * historical_multiplier * seasonal_multiplier
        predicted_score = max(0, min(100, predicted_score))  # Clamp to valid range
        
        # Calculate confidence interval
        uncertainty = (1 - confidence) * 20  # Max 20 point uncertainty
        uncertainty *= (days / 365)  # Increase uncertainty over time
        
        confidence_interval = (
            max(0, predicted_score - uncertainty),
            min(100, predicted_score + uncertainty)
        )
        
        # Determine predicted direction
        if predicted_score > current_score * 1.05:
            predicted_direction = TrendDirection.RISING
        elif predicted_score < current_score * 0.95:
            predicted_direction = TrendDirection.DECLINING
        else:
            predicted_direction = TrendDirection.STABLE
        
        # Identify key factors
        key_factors = []
        if abs(base_multiplier - 1.0) > 0.05:
            key_factors.append(f"Current trend direction: {current_direction.value}")
        if abs(historical_multiplier - 1.0) > 0.05:
            key_factors.append("Historical trend pattern")
        if abs(seasonal_multiplier - 1.0) > 0.1:
            key_factors.append("Seasonal effects")
        
        # Determine risk level
        risk_level = "low"
        if uncertainty > 15:
            risk_level = "high"
        elif uncertainty > 8:
            risk_level = "medium"
        
        return TrendForecast(
            timeframe=timeframe,
            predicted_score=round(predicted_score, 1),
            confidence_interval=(
                round(confidence_interval[0], 1),
                round(confidence_interval[1], 1)
            ),
            direction=predicted_direction,
            key_factors=key_factors,
            risk_level=risk_level
        )
    
    @classmethod
    def _calculate_historical_trend_multiplier(
        cls,
        historical_data: List[TrendData]
    ) -> float:
        """Calculate trend multiplier based on historical data."""
        scores = [data.trend_score for data in historical_data 
                 if data.trend_score is not None]
        
        if len(scores) < 3:
            return 1.0
        
        # Calculate trend slope
        n = len(scores)
        x_values = list(range(n))
        
        # Simple linear regression slope
        x_mean = mean(x_values)
        y_mean = mean(scores)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, scores))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 1.0
        
        slope = numerator / denominator
        
        # Convert slope to multiplier (normalize by time period)
        # Positive slope = upward trend, negative = downward
        multiplier = 1.0 + (slope / y_mean) * 0.5 if y_mean > 0 else 1.0
        
        # Clamp multiplier to reasonable range
        return max(0.5, min(2.0, multiplier))
    
    @classmethod
    def _calculate_seasonal_multiplier(
        cls,
        seasonal_analysis: Dict[str, Any],
        forecast_days: int
    ) -> float:
        """Calculate seasonal adjustment multiplier."""
        # Get current date and forecast date
        current_date = datetime.now()
        forecast_date = current_date + timedelta(days=forecast_days)
        
        # Get seasonal patterns
        monthly_averages = seasonal_analysis.get("monthly_averages", {})
        
        if not monthly_averages:
            return 1.0
        
        # Get scores for current and forecast months
        current_month_score = monthly_averages.get(current_date.month, 0)
        forecast_month_score = monthly_averages.get(forecast_date.month, 0)
        
        if current_month_score == 0:
            return 1.0
        
        # Calculate seasonal adjustment
        seasonal_ratio = forecast_month_score / current_month_score
        
        # Moderate the adjustment (don't apply full seasonal effect)
        seasonality_strength = seasonal_analysis.get("seasonality_strength", 0)
        adjustment = 1.0 + (seasonal_ratio - 1.0) * seasonality_strength * 0.5
        
        return max(0.5, min(2.0, adjustment))


async def validate_trend(
    trends_client: TrendsClient,
    cache_manager: CacheManager,
    keyword: str,
    timeframe: str = "today 12-m",
    include_forecasts: bool = True,
    include_seasonality: bool = True
) -> Dict[str, Any]:
    """Validate a trend comprehensively.
    
    Args:
        trends_client: Google Trends client
        cache_manager: Cache manager for performance
        keyword: Keyword to validate
        timeframe: Timeframe for analysis
        include_forecasts: Whether to generate forecasts
        include_seasonality: Whether to analyze seasonality
    
    Returns:
        Dictionary containing comprehensive trend validation
    """
    logger.info(f"Validating trend for keyword: {keyword}")
    
    try:
        # Get current trend analysis
        trend_analysis = await trends_client.get_trend_analysis(keyword, timeframe)
        
        if not trend_analysis:
            return {
                "error": "Unable to retrieve trend data",
                "keyword": keyword,
                "validation_timestamp": datetime.now().isoformat()
            }
        
        # Get historical data for enhanced analysis
        historical_data = None
        try:
            historical_data = await trends_client.get_raw_trend_data(
                keyword, timeframe="today 24-m"  # 2 years for better analysis
            )
        except Exception as e:
            logger.warning(f"Could not retrieve historical data: {e}")
        
        # Validate trend strength
        strength_validation = TrendValidator.validate_trend_strength(
            trend_analysis, historical_data
        )
        
        # Analyze seasonality
        seasonal_analysis = None
        if include_seasonality:
            seasonal_analysis = TrendValidator.analyze_seasonality(
                trend_analysis, historical_data
            )
        
        # Generate forecasts
        forecasts = []
        if include_forecasts:
            forecasts = TrendValidator.generate_forecasts(
                trend_analysis, historical_data, seasonal_analysis
            )
        
        # Assess sustainability
        sustainability_score = _calculate_sustainability_score(
            trend_analysis, strength_validation, seasonal_analysis, historical_data
        )
        
        # Identify risk factors
        risk_factors = _identify_risk_factors(
            trend_analysis, strength_validation, seasonal_analysis, forecasts
        )
        
        # Identify opportunities
        opportunities = _identify_opportunities(
            trend_analysis, strength_validation, seasonal_analysis, forecasts
        )
        
        # Generate recommendations
        recommendations = _generate_trend_recommendations(
            trend_analysis, strength_validation, seasonal_analysis, 
            forecasts, sustainability_score
        )
        
        # Create validation result
        validation_result = ValidationResult(
            keyword=keyword,
            is_valid=strength_validation["is_strong"] and sustainability_score >= 60,
            strength_score=strength_validation["strength_score"],
            sustainability_score=sustainability_score,
            seasonal_analysis=seasonal_analysis or {},
            forecasts=forecasts,
            risk_factors=risk_factors,
            opportunities=opportunities,
            recommendations=recommendations,
            validation_timestamp=datetime.now()
        )
        
        # Compile final result
        result = {
            "validation_result": {
                "keyword": validation_result.keyword,
                "is_valid": validation_result.is_valid,
                "overall_score": round((validation_result.strength_score + validation_result.sustainability_score) / 2, 1)
            },
            "trend_analysis": {
                "current_score": trend_analysis.trend_score,
                "direction": trend_analysis.direction.value,
                "strength": trend_analysis.strength.value,
                "confidence": trend_analysis.confidence_level
            },
            "strength_validation": strength_validation,
            "sustainability_analysis": {
                "score": sustainability_score,
                "factors": _get_sustainability_factors(sustainability_score)
            },
            "seasonal_analysis": seasonal_analysis,
            "forecasts": [
                {
                    "timeframe": f.timeframe,
                    "predicted_score": f.predicted_score,
                    "confidence_interval": f.confidence_interval,
                    "direction": f.direction.value,
                    "risk_level": f.risk_level,
                    "key_factors": f.key_factors
                }
                for f in forecasts
            ],
            "risk_assessment": {
                "risk_factors": risk_factors,
                "overall_risk": _calculate_overall_risk(risk_factors, forecasts)
            },
            "opportunities": opportunities,
            "recommendations": recommendations,
            "data_quality": {
                "has_historical_data": historical_data is not None,
                "data_points": len(historical_data) if historical_data else 0,
                "confidence_level": trend_analysis.confidence_level,
                "analysis_timeframe": timeframe
            },
            "validation_timestamp": validation_result.validation_timestamp.isoformat()
        }
        
        logger.info(f"Trend validation completed for: {keyword}")
        return result
    
    except Exception as e:
        logger.error(f"Trend validation failed for {keyword}: {e}")
        return {
            "error": str(e),
            "keyword": keyword,
            "validation_timestamp": datetime.now().isoformat()
        }


def _calculate_sustainability_score(
    trend_analysis: TrendAnalysis,
    strength_validation: Dict[str, Any],
    seasonal_analysis: Optional[Dict[str, Any]],
    historical_data: Optional[List[TrendData]]
) -> float:
    """Calculate trend sustainability score."""
    base_score = 50.0
    
    # Factor in trend strength
    base_score += (strength_validation["strength_score"] - 50) * 0.3
    
    # Factor in trend direction
    if trend_analysis.direction == TrendDirection.RISING:
        base_score += 15
    elif trend_analysis.direction == TrendDirection.DECLINING:
        base_score -= 20
    
    # Factor in confidence
    base_score += (trend_analysis.confidence_level - 0.5) * 40
    
    # Factor in seasonality (less seasonal = more sustainable)
    if seasonal_analysis:
        seasonality_strength = seasonal_analysis.get("seasonality_strength", 0)
        base_score -= seasonality_strength * 20
    
    # Factor in historical consistency
    if historical_data and len(historical_data) >= 6:
        scores = [d.trend_score for d in historical_data if d.trend_score is not None]
        if scores:
            volatility = stdev(scores) / mean(scores) if mean(scores) > 0 else 1
            base_score -= volatility * 30
    
    return max(0, min(100, base_score))


def _identify_risk_factors(
    trend_analysis: TrendAnalysis,
    strength_validation: Dict[str, Any],
    seasonal_analysis: Optional[Dict[str, Any]],
    forecasts: List[TrendForecast]
) -> List[str]:
    """Identify risk factors for the trend."""
    risk_factors = []
    
    # Add weakness factors from strength validation
    risk_factors.extend(strength_validation.get("weakness_factors", []))
    
    # Seasonal risks
    if seasonal_analysis and seasonal_analysis.get("seasonal_risk") == "high":
        risk_factors.append("High seasonal volatility may affect consistency")
    
    # Forecast risks
    declining_forecasts = [f for f in forecasts if f.direction == TrendDirection.DECLINING]
    if len(declining_forecasts) >= 2:
        risk_factors.append("Multiple forecasts show declining trend")
    
    high_risk_forecasts = [f for f in forecasts if f.risk_level == "high"]
    if high_risk_forecasts:
        risk_factors.append(f"High uncertainty in {len(high_risk_forecasts)} forecast(s)")
    
    # Confidence risks
    if trend_analysis.confidence_level < 0.4:
        risk_factors.append("Low confidence in trend data")
    
    return risk_factors


def _identify_opportunities(
    trend_analysis: TrendAnalysis,
    strength_validation: Dict[str, Any],
    seasonal_analysis: Optional[Dict[str, Any]],
    forecasts: List[TrendForecast]
) -> List[str]:
    """Identify opportunities from the trend analysis."""
    opportunities = []
    
    # Strong trend opportunities
    if strength_validation["is_strong"]:
        opportunities.append("Strong trend provides good market entry opportunity")
    
    # Rising trend opportunities
    if trend_analysis.direction == TrendDirection.RISING:
        opportunities.append("Rising trend suggests growing market interest")
    
    # Seasonal opportunities
    if seasonal_analysis and seasonal_analysis.get("peak_months"):
        peak_months = seasonal_analysis["peak_months"]
        current_month = datetime.now().month
        
        if current_month in peak_months:
            opportunities.append("Currently in peak season for this trend")
        else:
            next_peak = min([m for m in peak_months if m > current_month] + 
                           [m + 12 for m in peak_months if m <= current_month])
            months_to_peak = (next_peak - current_month) % 12
            opportunities.append(f"Peak season approaching in {months_to_peak} month(s)")
    
    # Forecast opportunities
    rising_forecasts = [f for f in forecasts if f.direction == TrendDirection.RISING]
    if rising_forecasts:
        opportunities.append(f"Positive growth predicted in {len(rising_forecasts)} forecast period(s)")
    
    return opportunities


def _generate_trend_recommendations(
    trend_analysis: TrendAnalysis,
    strength_validation: Dict[str, Any],
    seasonal_analysis: Optional[Dict[str, Any]],
    forecasts: List[TrendForecast],
    sustainability_score: float
) -> List[str]:
    """Generate actionable recommendations based on trend analysis."""
    recommendations = []
    
    # Overall trend recommendations
    if strength_validation["is_strong"] and sustainability_score >= 70:
        recommendations.append("Excellent trend - proceed with confidence")
    elif strength_validation["is_strong"]:
        recommendations.append("Good trend but monitor sustainability factors")
    elif sustainability_score >= 70:
        recommendations.append("Sustainable trend but consider strengthening market position")
    else:
        recommendations.append("Weak trend - consider alternative niches or wait for improvement")
    
    # Timing recommendations
    if seasonal_analysis and seasonal_analysis.get("has_seasonality"):
        peak_months = seasonal_analysis.get("peak_months", [])
        current_month = datetime.now().month
        
        if current_month in peak_months:
            recommendations.append("Optimal timing - launch during current peak season")
        elif peak_months:
            recommendations.append("Plan launch timing around seasonal peaks for maximum impact")
    
    # Forecast-based recommendations
    short_term_forecast = next((f for f in forecasts if f.timeframe == "3_months"), None)
    if short_term_forecast:
        if short_term_forecast.direction == TrendDirection.RISING:
            recommendations.append("Short-term growth expected - good time for market entry")
        elif short_term_forecast.direction == TrendDirection.DECLINING:
            recommendations.append("Short-term decline expected - consider delaying entry or focus on differentiation")
    
    # Risk mitigation recommendations
    if trend_analysis.confidence_level < 0.5:
        recommendations.append("Low data confidence - validate with additional market research")
    
    if seasonal_analysis and seasonal_analysis.get("seasonal_risk") == "high":
        recommendations.append("High seasonality - develop year-round content strategy")
    
    return recommendations


def _get_sustainability_factors(sustainability_score: float) -> List[str]:
    """Get factors that contribute to sustainability score."""
    if sustainability_score >= 80:
        return ["Highly sustainable trend with strong fundamentals"]
    elif sustainability_score >= 60:
        return ["Moderately sustainable with some risk factors"]
    elif sustainability_score >= 40:
        return ["Limited sustainability - requires careful monitoring"]
    else:
        return ["Low sustainability - high risk of trend decline"]


def _calculate_overall_risk(risk_factors: List[str], forecasts: List[TrendForecast]) -> str:
    """Calculate overall risk level."""
    risk_score = len(risk_factors) * 10
    
    # Add forecast risk
    high_risk_forecasts = len([f for f in forecasts if f.risk_level == "high"])
    risk_score += high_risk_forecasts * 15
    
    declining_forecasts = len([f for f in forecasts if f.direction == TrendDirection.DECLINING])
    risk_score += declining_forecasts * 10
    
    if risk_score >= 50:
        return "high"
    elif risk_score >= 25:
        return "medium"
    else:
        return "low"