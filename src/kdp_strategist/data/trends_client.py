"""Google Trends client for keyword and trend analysis.

Provides access to:
- Keyword trend data and popularity
- Regional interest analysis
- Related queries and topics
- Seasonal pattern detection
- Trend forecasting and validation

Features:
- Rate limiting and retry logic
- Comprehensive caching
- Error handling and logging
- Data validation and transformation
- Batch processing capabilities
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field

try:
    from pytrends.request import TrendReq
    from pytrends.exceptions import TooManyRequestsError, ResponseError
except ImportError:
    raise ImportError("pytrends library required. Install with: pip install pytrends")

import pandas as pd
import numpy as np
from .cache_manager import CacheManager
from ..models.trend_model import TrendAnalysis, TrendDirection, TrendStrength

logger = logging.getLogger(__name__)


@dataclass
class TrendsConfig:
    """Configuration for Google Trends client."""
    language: str = "en-US"
    timezone: int = 360  # UTC offset in minutes
    geo: str = "US"  # Default geographic location
    rate_limit_delay: float = 2.0  # Seconds between requests
    max_retries: int = 3
    retry_delay: float = 5.0
    timeout: int = 30
    cache_ttl: int = 7200  # 2 hours
    enable_caching: bool = True
    batch_size: int = 5  # Max keywords per batch


@dataclass
class TrendData:
    """Raw trend data from Google Trends."""
    keyword: str
    timeframe: str
    geo: str
    interest_over_time: pd.DataFrame = field(default_factory=pd.DataFrame)
    interest_by_region: pd.DataFrame = field(default_factory=pd.DataFrame)
    related_topics: Dict[str, pd.DataFrame] = field(default_factory=dict)
    related_queries: Dict[str, pd.DataFrame] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.last_updated is None:
            self.last_updated = datetime.now()


class RateLimiter:
    """Rate limiter for Google Trends requests."""
    
    def __init__(self, delay: float):
        self.delay = delay
        self.last_request = 0.0
    
    def wait_if_needed(self) -> None:
        """Wait if needed to respect rate limits."""
        now = time.time()
        time_since_last = now - self.last_request
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            logger.debug(f"Rate limiting: waiting {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
        
        self.last_request = time.time()


class TrendsClient:
    """Google Trends client with caching and rate limiting."""
    
    def __init__(self, config: TrendsConfig, cache_manager: Optional[CacheManager] = None):
        self.config = config
        self.cache_manager = cache_manager
        self.rate_limiter = RateLimiter(config.rate_limit_delay)
        
        # Initialize pytrends
        self.pytrends = TrendReq(
            hl=config.language,
            tz=config.timezone,
            timeout=config.timeout,
            retries=config.max_retries,
            backoff_factor=config.retry_delay
        )
        
        logger.info(f"Initialized Trends client for geo: {config.geo}")
    
    def get_trend_analysis(self, keyword: str, timeframe: str = "today 12-m", 
                          geo: Optional[str] = None, force_refresh: bool = False) -> Optional[TrendAnalysis]:
        """Get comprehensive trend analysis for a keyword."""
        geo = geo or self.config.geo
        
        # Check cache first
        if not force_refresh and self.config.enable_caching and self.cache_manager:
            cache_key = self.cache_manager.make_key("trends", "analysis", keyword, timeframe, geo)
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for trend analysis: {keyword}")
                return TrendAnalysis.from_dict(cached_data)
        
        # Get raw trend data
        trend_data = self.get_trend_data(keyword, timeframe, geo, force_refresh)
        if not trend_data:
            return None
        
        # Analyze the trend data
        analysis = self._analyze_trend_data(trend_data)
        
        # Cache the result
        if self.config.enable_caching and self.cache_manager:
            cache_key = self.cache_manager.make_key("trends", "analysis", keyword, timeframe, geo)
            self.cache_manager.set(cache_key, analysis.to_dict(), self.config.cache_ttl)
        
        logger.info(f"Generated trend analysis for keyword: {keyword}")
        return analysis
    
    def get_trend_data(self, keyword: str, timeframe: str = "today 12-m", 
                      geo: Optional[str] = None, force_refresh: bool = False) -> Optional[TrendData]:
        """Get raw trend data for a keyword."""
        geo = geo or self.config.geo
        
        # Check cache first
        if not force_refresh and self.config.enable_caching and self.cache_manager:
            cache_key = self.cache_manager.make_key("trends", "raw", keyword, timeframe, geo)
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for trend data: {keyword}")
                return self._deserialize_trend_data(cached_data)
        
        # Fetch from Google Trends
        try:
            self.rate_limiter.wait_if_needed()
            
            # Build payload
            self.pytrends.build_payload(
                kw_list=[keyword],
                cat=0,
                timeframe=timeframe,
                geo=geo,
                gprop=''
            )
            
            # Get interest over time
            interest_over_time = self.pytrends.interest_over_time()
            if interest_over_time.empty:
                logger.warning(f"No trend data found for keyword: {keyword}")
                return None
            
            # Get interest by region
            interest_by_region = pd.DataFrame()
            try:
                self.rate_limiter.wait_if_needed()
                interest_by_region = self.pytrends.interest_by_region(resolution='COUNTRY', inc_low_vol=True, inc_geo_code=False)
            except Exception as e:
                logger.warning(f"Failed to get regional interest for {keyword}: {e}")
            
            # Get related topics
            related_topics = {}
            try:
                self.rate_limiter.wait_if_needed()
                topics = self.pytrends.related_topics()
                if keyword in topics:
                    related_topics = topics[keyword]
            except Exception as e:
                logger.warning(f"Failed to get related topics for {keyword}: {e}")
            
            # Get related queries
            related_queries = {}
            try:
                self.rate_limiter.wait_if_needed()
                queries = self.pytrends.related_queries()
                if keyword in queries:
                    related_queries = queries[keyword]
            except Exception as e:
                logger.warning(f"Failed to get related queries for {keyword}: {e}")
            
            # Get suggestions
            suggestions = []
            try:
                self.rate_limiter.wait_if_needed()
                suggestions = self.pytrends.suggestions(keyword=keyword)
                suggestions = [s.get('title', '') for s in suggestions if s.get('title')]
            except Exception as e:
                logger.warning(f"Failed to get suggestions for {keyword}: {e}")
            
            # Create trend data object
            trend_data = TrendData(
                keyword=keyword,
                timeframe=timeframe,
                geo=geo,
                interest_over_time=interest_over_time,
                interest_by_region=interest_by_region,
                related_topics=related_topics,
                related_queries=related_queries,
                suggestions=suggestions
            )
            
            # Cache the result
            if self.config.enable_caching and self.cache_manager:
                cache_key = self.cache_manager.make_key("trends", "raw", keyword, timeframe, geo)
                serialized_data = self._serialize_trend_data(trend_data)
                self.cache_manager.set(cache_key, serialized_data, self.config.cache_ttl)
            
            logger.info(f"Retrieved trend data for keyword: {keyword}")
            return trend_data
        
        except TooManyRequestsError:
            logger.error(f"Rate limited by Google Trends for keyword: {keyword}")
            return None
        
        except ResponseError as e:
            logger.error(f"Google Trends API error for keyword {keyword}: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to get trend data for keyword {keyword}: {e}")
            return None
    
    def compare_keywords(self, keywords: List[str], timeframe: str = "today 12-m", 
                        geo: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Compare multiple keywords in a single request."""
        if len(keywords) > self.config.batch_size:
            logger.warning(f"Too many keywords ({len(keywords)}), limiting to {self.config.batch_size}")
            keywords = keywords[:self.config.batch_size]
        
        geo = geo or self.config.geo
        
        try:
            self.rate_limiter.wait_if_needed()
            
            # Build payload for comparison
            self.pytrends.build_payload(
                kw_list=keywords,
                cat=0,
                timeframe=timeframe,
                geo=geo,
                gprop=''
            )
            
            # Get interest over time for comparison
            comparison_data = self.pytrends.interest_over_time()
            
            if comparison_data.empty:
                logger.warning(f"No comparison data found for keywords: {keywords}")
                return None
            
            logger.info(f"Retrieved comparison data for {len(keywords)} keywords")
            return comparison_data
        
        except Exception as e:
            logger.error(f"Failed to compare keywords {keywords}: {e}")
            return None
    
    def get_trending_searches(self, geo: Optional[str] = None) -> List[str]:
        """Get current trending searches."""
        geo = geo or self.config.geo
        
        try:
            self.rate_limiter.wait_if_needed()
            
            trending = self.pytrends.trending_searches(pn=geo)
            if trending.empty:
                return []
            
            # Extract trending terms
            trending_terms = trending[0].tolist()
            
            logger.info(f"Retrieved {len(trending_terms)} trending searches for {geo}")
            return trending_terms
        
        except Exception as e:
            logger.error(f"Failed to get trending searches for {geo}: {e}")
            return []
    
    def get_top_charts(self, year: int, geo: Optional[str] = None, category: str = "all") -> List[str]:
        """Get top charts for a specific year."""
        geo = geo or self.config.geo
        
        try:
            self.rate_limiter.wait_if_needed()
            
            top_charts = self.pytrends.top_charts(year, hl=self.config.language, tz=self.config.timezone, geo=geo)
            if top_charts.empty:
                return []
            
            # Extract top terms
            top_terms = top_charts['title'].tolist() if 'title' in top_charts.columns else []
            
            logger.info(f"Retrieved {len(top_terms)} top chart terms for {year}")
            return top_terms
        
        except Exception as e:
            logger.error(f"Failed to get top charts for {year}: {e}")
            return []
    
    def _analyze_trend_data(self, trend_data: TrendData) -> TrendAnalysis:
        """Analyze raw trend data and create TrendAnalysis object."""
        interest_data = trend_data.interest_over_time
        keyword = trend_data.keyword
        
        if interest_data.empty or keyword not in interest_data.columns:
            # Return minimal analysis for empty data
            return TrendAnalysis(
                keyword=keyword,
                trend_score=0,
                direction=TrendDirection.STABLE,
                strength=TrendStrength.WEAK,
                confidence_level=0.0
            )
        
        # Get the interest values
        values = interest_data[keyword].values
        dates = interest_data.index
        
        # Calculate trend score (average interest)
        trend_score = float(np.mean(values))
        
        # Determine trend direction
        if len(values) >= 2:
            # Use linear regression to determine overall direction
            x = np.arange(len(values))
            slope = np.polyfit(x, values, 1)[0]
            
            if slope > 1:
                direction = TrendDirection.RISING
            elif slope < -1:
                direction = TrendDirection.DECLINING
            else:
                direction = TrendDirection.STABLE
        else:
            direction = TrendDirection.STABLE
        
        # Determine trend strength
        max_val = float(np.max(values))
        std_val = float(np.std(values))
        
        if max_val >= 80 and std_val <= 10:
            strength = TrendStrength.VERY_STRONG
        elif max_val >= 60 and std_val <= 20:
            strength = TrendStrength.STRONG
        elif max_val >= 40 and std_val <= 30:
            strength = TrendStrength.MODERATE
        elif max_val >= 20:
            strength = TrendStrength.WEAK
        else:
            strength = TrendStrength.VERY_WEAK
        
        # Calculate confidence level
        data_points = len(values)
        non_zero_points = np.count_nonzero(values)
        confidence_level = min(1.0, (non_zero_points / max(data_points, 1)) * (max_val / 100))
        
        # Extract regional interest
        regional_interest = {}
        if not trend_data.interest_by_region.empty:
            region_data = trend_data.interest_by_region[keyword] if keyword in trend_data.interest_by_region.columns else pd.Series()
            regional_interest = region_data.to_dict()
        
        # Extract related queries
        related_queries = []
        if trend_data.related_queries:
            for query_type, queries_df in trend_data.related_queries.items():
                if not queries_df.empty and 'query' in queries_df.columns:
                    related_queries.extend(queries_df['query'].tolist()[:10])  # Top 10
        
        # Detect seasonal patterns
        seasonal_patterns = self._detect_seasonal_patterns(values, dates)
        
        # Generate 6-month forecast
        forecast_6m = self._generate_forecast(values, 6)
        
        return TrendAnalysis(
            keyword=keyword,
            trend_score=trend_score,
            direction=direction,
            strength=strength,
            regional_interest=regional_interest,
            related_queries=related_queries,
            seasonal_patterns=seasonal_patterns,
            forecast_6m=forecast_6m,
            confidence_level=confidence_level,
            data_points=data_points,
            timeframe=trend_data.timeframe,
            geo=trend_data.geo,
            last_updated=trend_data.last_updated
        )
    
    def _detect_seasonal_patterns(self, values: np.ndarray, dates: pd.DatetimeIndex) -> Dict[str, Any]:
        """Detect seasonal patterns in trend data."""
        if len(values) < 12:  # Need at least a year of data
            return {}
        
        try:
            # Group by month to detect seasonal patterns
            monthly_avg = {}
            for i, date in enumerate(dates):
                month = date.month
                if month not in monthly_avg:
                    monthly_avg[month] = []
                monthly_avg[month].append(values[i])
            
            # Calculate average for each month
            monthly_patterns = {}
            for month, vals in monthly_avg.items():
                monthly_patterns[month] = float(np.mean(vals))
            
            # Find peak and low seasons
            if monthly_patterns:
                peak_month = max(monthly_patterns.keys(), key=lambda k: monthly_patterns[k])
                low_month = min(monthly_patterns.keys(), key=lambda k: monthly_patterns[k])
                
                return {
                    "monthly_averages": monthly_patterns,
                    "peak_month": peak_month,
                    "low_month": low_month,
                    "seasonality_strength": float(np.std(list(monthly_patterns.values())))
                }
        
        except Exception as e:
            logger.warning(f"Failed to detect seasonal patterns: {e}")
        
        return {}
    
    def _generate_forecast(self, values: np.ndarray, months: int) -> List[float]:
        """Generate simple forecast for the next N months."""
        if len(values) < 3:
            return []
        
        try:
            # Simple linear extrapolation
            x = np.arange(len(values))
            coeffs = np.polyfit(x, values, min(2, len(values) - 1))  # Linear or quadratic
            
            # Generate forecast points
            forecast = []
            for i in range(months):
                future_x = len(values) + i
                if len(coeffs) == 2:  # Linear
                    predicted = coeffs[0] * future_x + coeffs[1]
                else:  # Quadratic
                    predicted = coeffs[0] * future_x**2 + coeffs[1] * future_x + coeffs[2]
                
                # Ensure forecast is within reasonable bounds
                predicted = max(0, min(100, predicted))
                forecast.append(float(predicted))
            
            return forecast
        
        except Exception as e:
            logger.warning(f"Failed to generate forecast: {e}")
            return []
    
    def _serialize_trend_data(self, trend_data: TrendData) -> Dict[str, Any]:
        """Serialize TrendData for caching."""
        return {
            "keyword": trend_data.keyword,
            "timeframe": trend_data.timeframe,
            "geo": trend_data.geo,
            "interest_over_time": trend_data.interest_over_time.to_json() if not trend_data.interest_over_time.empty else "",
            "interest_by_region": trend_data.interest_by_region.to_json() if not trend_data.interest_by_region.empty else "",
            "related_topics": {k: v.to_json() if not v.empty else "" for k, v in trend_data.related_topics.items()},
            "related_queries": {k: v.to_json() if not v.empty else "" for k, v in trend_data.related_queries.items()},
            "suggestions": trend_data.suggestions,
            "last_updated": trend_data.last_updated.isoformat() if trend_data.last_updated else None,
        }
    
    def _deserialize_trend_data(self, data: Dict[str, Any]) -> TrendData:
        """Deserialize TrendData from cache."""
        # Deserialize DataFrames
        interest_over_time = pd.read_json(data["interest_over_time"]) if data["interest_over_time"] else pd.DataFrame()
        interest_by_region = pd.read_json(data["interest_by_region"]) if data["interest_by_region"] else pd.DataFrame()
        
        related_topics = {}
        for k, v in data.get("related_topics", {}).items():
            related_topics[k] = pd.read_json(v) if v else pd.DataFrame()
        
        related_queries = {}
        for k, v in data.get("related_queries", {}).items():
            related_queries[k] = pd.read_json(v) if v else pd.DataFrame()
        
        # Handle datetime
        last_updated = None
        if data.get("last_updated"):
            last_updated = datetime.fromisoformat(data["last_updated"])
        
        return TrendData(
            keyword=data["keyword"],
            timeframe=data["timeframe"],
            geo=data["geo"],
            interest_over_time=interest_over_time,
            interest_by_region=interest_by_region,
            related_topics=related_topics,
            related_queries=related_queries,
            suggestions=data.get("suggestions", []),
            last_updated=last_updated
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = {
            "rate_limit_delay": self.config.rate_limit_delay,
            "cache_enabled": self.config.enable_caching,
            "geo": self.config.geo,
            "language": self.config.language,
        }
        
        if self.cache_manager:
            stats["cache_stats"] = self.cache_manager.get_stats()
        
        return stats
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass